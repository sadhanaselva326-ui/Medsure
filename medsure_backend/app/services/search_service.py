"""search_service.py - Production-grade medicine full-text and fuzzy search.

Performance improvements (v2):
- Replaced broad selectinload(variants -> manufacturer) with correlated scalar
  subqueries per variant field, eliminating the O(n * variants) N+1 load.
- Replaced subquery-based COUNT(*) with COUNT(*) OVER() window function so the
  total row count is fetched in the same query pass as the results.
- Removed Python-level SequenceMatcher relevance scoring (redundant post-sort).
- Fixed session dialect detection via settings.DATABASE_URL (avoids deprecated
  session.get_bind() which is not supported in async sessions).
- Uses DISTINCT ON (medicine_id) for manufacturer filter instead of subquery-distinct.
"""
import math
from typing import List, Optional
from sqlalchemy import select, func, or_, and_, desc, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.manufacturer import Manufacturer
from app.schemas.medicine import MedicineSearchResultItem
from app.schemas.common import PaginatedResponse, PaginationMeta


def _session_is_postgres(session: AsyncSession) -> bool:
    """Detect the dialect of the session's underlying engine.

    Uses sync_session.get_bind() — the correct SQLAlchemy 2.0 async-safe
    pattern that works both with the production asyncpg engine and with SQLite
    in-memory test sessions, without relying on settings.DATABASE_URL (which
    always reflects the production config regardless of test overrides).
    """
    try:
        bind = session.sync_session.get_bind()
        return bind.dialect.name == "postgresql"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Correlated scalar subqueries for first-variant fields
# ---------------------------------------------------------------------------
# These select a single value from medicine_variants for the parent medicine,
# ordered by mrp ASC NULLS LAST (cheapest / first added pack).
# They use the idx_variants_medicine_id B-tree index and avoid loading full ORM
# objects across all variants just to read one field.
# ---------------------------------------------------------------------------

def _variant_scalar_subq(column_name: str):
    """Correlated scalar subquery: cheapest variant's <column_name> for each medicine."""
    mv = MedicineVariant.__table__
    col = getattr(mv.c, column_name)
    return (
        select(col)
        .where(mv.c.medicine_id == Medicine.__table__.c.medicine_id)
        .order_by(mv.c.mrp.asc().nulls_last())
        .limit(1)
        .correlate(Medicine.__table__)
        .scalar_subquery()
    )


def _variant_mfg_name_subq():
    """Correlated scalar subquery: manufacturer name of the cheapest variant."""
    mv = MedicineVariant.__table__
    mfg = Manufacturer.__table__
    return (
        select(mfg.c.name)
        .select_from(
            mv.join(mfg, mv.c.manufacturer_id == mfg.c.manufacturer_id, isouter=True)
        )
        .where(mv.c.medicine_id == Medicine.__table__.c.medicine_id)
        .order_by(mv.c.mrp.asc().nulls_last())
        .limit(1)
        .correlate(Medicine.__table__)
        .scalar_subquery()
    )


async def search_medicines(
    session: AsyncSession,
    query: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    dosage_form: Optional[str] = None,
    strength: Optional[str] = None,
    prescription_status: Optional[str] = None,
    manufacturer_name: Optional[str] = None,
) -> PaginatedResponse[MedicineSearchResultItem]:
    """Production-grade Medicine search supporting PostgreSQL FTS (tsvector) +
    pg_trgm fuzzy similarity matching with graceful filtering and pagination.

    v2 optimizations:
    - Correlated scalar subqueries replace selectinload(variants) entirely.
    - COUNT(*) OVER() window function avoids a second count query round-trip.
    - No Python-level string similarity; relevance comes from the DB ORDER BY.
    - DISTINCT ON replaces subquery-level distinct for the manufacturer filter.
    """
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit

    is_pg = _session_is_postgres(session)

    # ------------------------------------------------------------------
    # Column list: medicine fields + correlated variant subqueries
    # ------------------------------------------------------------------
    mfg_name_col = _variant_mfg_name_subq().label("manufacturer_name")
    mrp_col = _variant_scalar_subq("mrp").label("first_mrp")
    pack_size_col = _variant_scalar_subq("pack_size").label("first_pack_size")
    unit_col = _variant_scalar_subq("unit").label("first_unit")

    base_cols = [
        Medicine.medicine_id,
        Medicine.brand_name,
        Medicine.generic_name,
        Medicine.strength,
        Medicine.dosage_form,
        Medicine.prescription_status,
        Medicine.is_discontinued,
        Medicine.source_id,
        Medicine.source_name,
        Medicine.is_demo,
        Medicine.confidence_score,
        mfg_name_col,
        mrp_col,
        pack_size_col,
        unit_col,
    ]

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------
    filters = [Medicine.is_discontinued == False]  # noqa: E712

    if dosage_form:
        filters.append(func.lower(Medicine.dosage_form) == dosage_form.strip().lower())
    if strength:
        filters.append(func.lower(Medicine.strength) == strength.strip().lower())
    if prescription_status:
        filters.append(
            func.lower(Medicine.prescription_status) == prescription_status.strip().lower()
        )

    # Manufacturer filter using correlated EXISTS subquery.
    # Avoids outer query joins that duplicate medicine rows, eliminates the need for
    # DISTINCT ON (which conflicts with ORDER BY relevance), and preserves exact COUNT(*) OVER().
    if manufacturer_name and manufacturer_name.strip():
        m_name_clean = manufacturer_name.strip().lower()
        mv = MedicineVariant.__table__
        mfg = Manufacturer.__table__
        mfg_subq = (
            select(1)
            .select_from(
                mv.join(mfg, mv.c.manufacturer_id == mfg.c.manufacturer_id)
            )
            .where(
                mv.c.medicine_id == Medicine.__table__.c.medicine_id,
                func.lower(mfg.c.name).contains(m_name_clean),
            )
            .correlate(Medicine.__table__)
        )
        filters.append(mfg_subq.exists())

    # ------------------------------------------------------------------
    # Full-text + trigram search
    # ------------------------------------------------------------------
    relevance_col = None
    if query and query.strip():
        q_clean = query.strip()
        if is_pg:
            tsquery = func.plainto_tsquery("english", q_clean)
            brand_tsvec = func.to_tsvector("english", Medicine.brand_name)
            generic_tsvec = func.to_tsvector("english", Medicine.generic_name)

            # Each OR arm hits its own GIN index via BitmapOr plan.
            fts_cond = or_(
                brand_tsvec.op("@@")(tsquery),
                generic_tsvec.op("@@")(tsquery),
            )
            # % operator uses gin_trgm_ops indexes
            # (equivalent to similarity() >= pg_trgm.similarity_threshold = 0.3)
            trgm_cond = or_(
                Medicine.brand_name.op("%")(q_clean),
                Medicine.generic_name.op("%")(q_clean),
            )
            # DB-computed composite relevance score (no Python overhead)
            relevance_col = (
                func.ts_rank(brand_tsvec, tsquery) * 2.0
                + func.similarity(Medicine.brand_name, q_clean)
                + func.similarity(Medicine.generic_name, q_clean) * 0.7
            ).label("relevance")
            base_cols.append(relevance_col)

            like_pat = f"%{q_clean}%"
            mv_tbl = MedicineVariant.__table__
            mfg_tbl = Manufacturer.__table__
            mfg_like_subq = (
                select(1)
                .select_from(
                    mv_tbl.join(mfg_tbl, mv_tbl.c.manufacturer_id == mfg_tbl.c.manufacturer_id, isouter=True)
                )
                .where(
                    mv_tbl.c.medicine_id == Medicine.__table__.c.medicine_id,
                    mfg_tbl.c.name.ilike(like_pat),
                )
                .correlate(Medicine.__table__)
            )
            filters.append(
                or_(
                    fts_cond,
                    trgm_cond,
                    Medicine.strength.ilike(like_pat),
                    Medicine.dosage_form.ilike(like_pat),
                    mfg_like_subq.exists(),
                )
            )
        else:
            # SQLite / other engine ILIKE fallback
            like_pat = f"%{q_clean}%"
            mv_tbl = MedicineVariant.__table__
            mfg_tbl = Manufacturer.__table__
            mfg_like_subq = (
                select(1)
                .select_from(
                    mv_tbl.join(mfg_tbl, mv_tbl.c.manufacturer_id == mfg_tbl.c.manufacturer_id, isouter=True)
                )
                .where(
                    mv_tbl.c.medicine_id == Medicine.__table__.c.medicine_id,
                    mfg_tbl.c.name.ilike(like_pat),
                )
                .correlate(Medicine.__table__)
            )
            filters.append(
                or_(
                    Medicine.brand_name.ilike(like_pat),
                    Medicine.generic_name.ilike(like_pat),
                    Medicine.strength.ilike(like_pat),
                    Medicine.dosage_form.ilike(like_pat),
                    mfg_like_subq.exists(),
                )
            )
            base_cols.append(literal_column("1.0").label("relevance"))
    else:
        base_cols.append(literal_column("1.0").label("relevance"))

    # ------------------------------------------------------------------
    # Build candidate query
    # ------------------------------------------------------------------
    stmt = select(*base_cols).where(and_(*filters))

    # ------------------------------------------------------------------
    # Window function COUNT(*) OVER () — same query pass, no second RTT
    # ------------------------------------------------------------------
    count_col = func.count(Medicine.medicine_id).over().label("_total_count")
    stmt_paged = stmt.add_columns(count_col)

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------
    if relevance_col is not None:
        stmt_paged = stmt_paged.order_by(desc(relevance_col))
    else:
        stmt_paged = stmt_paged.order_by(Medicine.brand_name.asc())

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------
    stmt_paged = stmt_paged.offset(offset).limit(limit)

    result = await session.execute(stmt_paged)
    rows = result.mappings().all()

    # ------------------------------------------------------------------
    # Assemble output — no ORM objects, pure row mappings
    # ------------------------------------------------------------------
    total = 0
    items: List[MedicineSearchResultItem] = []

    for row in rows:
        if total == 0:
            total = int(row["_total_count"] or 0)

        mrp_val = float(row["first_mrp"]) if row["first_mrp"] is not None else None
        conf = float(row["confidence_score"]) if row["confidence_score"] is not None else 0.85
        rel = float(row.get("relevance") or 1.0)
        # Clamp to [0.05, 1.0] — ts_rank can return very small floats
        rel = max(0.05, min(1.0, rel))

        items.append(
            MedicineSearchResultItem(
                medicine_id=row["medicine_id"],
                brand_name=row["brand_name"],
                generic_name=row["generic_name"],
                strength=row["strength"],
                dosage_form=row["dosage_form"],
                manufacturer=row["manufacturer_name"],
                mrp=mrp_val,
                pack_size=row["first_pack_size"],
                unit=row["first_unit"],
                source=row.get("source_name"),
                source_name=row.get("source_name"),
                is_demo=bool(row.get("is_demo", False)),
                confidence_score=conf,
                relevance_score=rel,
            )
        )

    total_pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )

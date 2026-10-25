"""002_search_perf_indexes

Add performance indexes to accelerate the v2 search service:
  1. Partial index on medicines.is_discontinued = FALSE — filters 100% of search
     rows but was previously a full-table boolean scan.
  2. Composite index on medicine_variants (medicine_id, mrp, pack_size, unit) —
     covers the correlated scalar subqueries emitted by _variant_scalar_subq()
     with an index-only scan (no heap access required).
  3. SET pg_trgm.similarity_threshold at the session level hint (documentation
     only — applied in app startup or via postgresql.conf for the live DB).

Revision ID: 002_search_perf_indexes
Revises:     001_initial_schema
Create Date: 2026-10-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_search_perf_indexes"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Partial GIN FTS index — only indexes non-discontinued medicines.
    #    Reduces index size by ~<1% (most rows are active) but eliminates a
    #    boolean filter step from every search plan since PostgreSQL can use
    #    the partial index directly when the WHERE clause matches.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_medicines_brand_name_active
        ON medicines USING gin(to_tsvector('english', brand_name))
        WHERE is_discontinued = FALSE;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_medicines_generic_name_active
        ON medicines USING gin(to_tsvector('english', generic_name))
        WHERE is_discontinued = FALSE;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_medicines_brand_trgm_active
        ON medicines USING gin(brand_name gin_trgm_ops)
        WHERE is_discontinued = FALSE;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_medicines_generic_trgm_active
        ON medicines USING gin(generic_name gin_trgm_ops)
        WHERE is_discontinued = FALSE;
        """
    )

    # 2. Covering index for the correlated variant scalar subquery.
    #    The search_service._variant_scalar_subq() emits:
    #        SELECT mrp / pack_size / unit
    #        FROM   medicine_variants
    #        WHERE  medicine_id = $1
    #        ORDER  BY mrp ASC NULLS LAST
    #        LIMIT  1
    #    With this covering index PostgreSQL can satisfy the entire subquery via
    #    an Index Only Scan — no heap access needed for the included columns.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_variants_med_mrp_cover
        ON medicine_variants (medicine_id, mrp ASC NULLS LAST)
        INCLUDE (pack_size, unit, manufacturer_id);
        """
    )

    # 3. Covering index for the manufacturer name subquery join.
    #    _variant_mfg_name_subq() joins medicine_variants -> manufacturers using
    #    manufacturer_id.  This index allows the planner to use an index scan on
    #    the join column directly on the already-ordered variant rows.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_variants_mfg_cover
        ON medicine_variants (medicine_id, manufacturer_id, mrp ASC NULLS LAST);
        """
    )

    # 4. Index on medicines (is_discontinued, brand_name) used for the default
    #    brand_name ASC sort on the non-query (browse all) path.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_medicines_active_brand
        ON medicines (brand_name)
        WHERE is_discontinued = FALSE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_medicines_active_brand;")
    op.execute("DROP INDEX IF EXISTS idx_variants_mfg_cover;")
    op.execute("DROP INDEX IF EXISTS idx_variants_med_mrp_cover;")
    op.execute("DROP INDEX IF EXISTS idx_medicines_generic_trgm_active;")
    op.execute("DROP INDEX IF EXISTS idx_medicines_brand_trgm_active;")
    op.execute("DROP INDEX IF EXISTS idx_medicines_generic_name_active;")
    op.execute("DROP INDEX IF EXISTS idx_medicines_brand_name_active;")

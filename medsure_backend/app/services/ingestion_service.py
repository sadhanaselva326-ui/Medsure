import os
import io
import csv
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID
import httpx
from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sources import DataSource
from app.models.manufacturer import Manufacturer
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.codes import MedicineCode
from app.schemas.ingestion import IngestRequest, IngestStats
from app.utils.helpers import (
    normalize_text,
    clean_salt_name,
    extract_strength_string,
    parse_pack_size_label,
    build_medicine_dedup_keys,
)

logger = logging.getLogger("medsure.ingestion")


def _clean_price(val: Any) -> Optional[float]:
    """Safely extracts float price from raw string or number."""
    if val is None or val == "":
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val) if float(val) >= 0 else None
        cleaned = str(val).replace("₹", "").replace(",", "").replace("Rs.", "").replace("Rs", "").strip()
        f = float(cleaned)
        return f if f >= 0 else None
    except Exception:
        return None


def _clean_integer(val: Any) -> Optional[int]:
    """Safely extracts integer value."""
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).strip()))
    except Exception:
        return None


async def ingest_dataset(
    session: AsyncSession,
    payload: IngestRequest,
    progress_callback: Optional[Callable[[int, int, IngestStats], None]] = None,
) -> IngestStats:
    """Production-grade Medicine dataset ingestion engine.

    Supports:
    - Configurable batch processing with per-batch transactional commits
    - Parent medicine deduplication (brand + generic/salt + dosage + strength)
    - Variant deduplication and reuse for multi-pack sizes
    - Robust packaging label parsing (tablets, capsules, bottles, syrups, inhalers, etc.)
    - Safe error isolation per batch without data loss
    """
    # 1. Verify data source exists
    source_stmt = select(DataSource).where(DataSource.source_id == payload.source_id)
    source_res = await session.execute(source_stmt)
    source = source_res.scalar_one_or_none()
    if not source:
        raise ValueError(f"Data source with ID '{payload.source_id}' does not exist.")

    # 2. Extract records into a list or stream
    all_records: List[Dict[str, Any]] = []

    if payload.raw_data:
        all_records = payload.raw_data
    elif payload.file_url:
        target = payload.file_url.strip()
        if target.startswith("http://") or target.startswith("https://"):
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(target)
                resp.raise_for_status()
                content = resp.text
        elif os.path.exists(target):
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            raise ValueError(f"File not found: {target}")

        fmt = payload.format.lower().strip()
        if fmt == "csv":
            reader = csv.DictReader(io.StringIO(content))
            all_records = list(reader)
        elif fmt == "json":
            parsed = json.loads(content)
            all_records = parsed if isinstance(parsed, list) else [parsed]
        else:
            raise ValueError(f"Unsupported format: {payload.format}")

    total_rows = len(all_records)
    stats = IngestStats(
        source_id=source.source_id,
        source_name=source.source_name,
        total_processed=total_rows,
    )

    if not all_records:
        return stats

    # 3. Preload existing manufacturers into memory cache
    mfg_stmt = select(Manufacturer)
    mfg_res = await session.execute(mfg_stmt)
    existing_mfgs: Dict[str, Manufacturer] = {
        normalize_text(m.name): m for m in mfg_res.scalars().all() if m.name
    }

    # 4. Preload existing medicines and variants into dedup index
    med_stmt = select(Medicine).options(selectinload(Medicine.variants))
    med_res = await session.execute(med_stmt)
    existing_medicines = med_res.scalars().all()

    # Index mapping: dedup_key -> Medicine
    med_cache: Dict[str, Medicine] = {}
    # Index mapping: medicine_id -> dict of (pack_size, unit) -> MedicineVariant
    med_variants: Dict[UUID, Dict[Tuple[Optional[int], Optional[str]], MedicineVariant]] = {}

    for m in existing_medicines:
        keys = build_medicine_dedup_keys(m.brand_name, m.generic_name, m.dosage_form, m.strength)
        for k in keys:
            if k not in med_cache:
                med_cache[k] = m
        med_variants[m.medicine_id] = {
            (v.pack_size, (v.unit or "").lower().strip() if v.unit else None): v
            for v in m.variants
        }

    # Preload existing GTINs to prevent unique constraint collisions
    code_stmt = select(MedicineCode.gtin).where(MedicineCode.gtin.isnot(None))
    code_res = await session.execute(code_stmt)
    existing_gtins: Set[str] = {c for c in code_res.scalars().all() if c}

    batch_size = max(10, min(5000, payload.batch_size))
    total_batches = (total_rows + batch_size - 1) // batch_size

    # 5. Process in batches
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_rows)
        batch = all_records[start_idx:end_idx]

        batch_new_meds = 0
        batch_reused_meds = 0
        batch_variants = 0
        batch_duplicates = 0
        batch_failed = 0
        batch_skipped = 0

        try:
            for row_offset, row in enumerate(batch):
                abs_row_idx = start_idx + row_offset
                try:
                    raw_brand = row.get("brand_name") or row.get("name") or row.get("medicine_name")
                    raw_generic = (
                        row.get("generic_name")
                        or row.get("composition")
                        or row.get("short_composition")
                        or row.get("salt_composition")
                        or raw_brand
                    )

                    if not raw_brand or not raw_generic:
                        batch_skipped += 1
                        continue

                    brand_str = str(raw_brand).strip()
                    generic_str = str(raw_generic).strip()
                    raw_dosage = row.get("dosage_form") or row.get("type") or "Tablet"
                    dosage_form = str(raw_dosage).strip() if raw_dosage else "Tablet"

                    # Parse pack size & unit
                    raw_pack_label = (
                        row.get("pack_size_label")
                        or row.get("packaging_description")
                        or row.get("pack_size")
                    )
                    parsed_pack, parsed_unit, parsed_desc = parse_pack_size_label(
                        raw_pack_label,
                        default_dosage_form=dosage_form,
                    )
                    # If row has explicit pack_size integer, override
                    if row.get("pack_size") is not None and str(row.get("pack_size")).strip().isdigit():
                        parsed_pack = _clean_integer(row.get("pack_size"))
                    if row.get("unit") and str(row.get("unit")).strip():
                        parsed_unit = str(row.get("unit")).strip().lower()

                    # Parse strength
                    strength_str = extract_strength_string(
                        row.get("strength"),
                        fallback_text=f"{brand_str} {generic_str}",
                    )

                    # Manufacturer check & reuse
                    mfg_obj = None
                    mfg_name = row.get("manufacturer") or row.get("manufacturer_name")
                    if mfg_name:
                        mfg_clean = str(mfg_name).strip()
                        norm_mfg = normalize_text(mfg_clean)
                        if norm_mfg in existing_mfgs:
                            mfg_obj = existing_mfgs[norm_mfg]
                        else:
                            mfg_obj = Manufacturer(
                                name=mfg_clean,
                                source_id=source.source_id,
                                verification_status="verified" if source.verification_status == "verified" else "pending",
                            )
                            session.add(mfg_obj)
                            await session.flush()
                            existing_mfgs[norm_mfg] = mfg_obj
                            stats.manufacturers_created += 1

                    # Medicine deduplication
                    dedup_keys = build_medicine_dedup_keys(brand_str, generic_str, dosage_form, strength_str)
                    matched_med: Optional[Medicine] = None

                    for k in dedup_keys:
                        if k in med_cache:
                            matched_med = med_cache[k]
                            break

                    if matched_med:
                        # Existing medicine reused!
                        med = matched_med
                        batch_reused_meds += 1
                        # Update missing details if new row has them
                        if not med.strength and strength_str:
                            med.strength = strength_str
                        if not med.dosage_form and dosage_form:
                            med.dosage_form = dosage_form
                    else:
                        # Create brand-new parent Medicine
                        clean_comp = {
                            "raw": generic_str,
                            "active_ingredients": [],
                            "excipients": [],
                        }
                        med = Medicine(
                            brand_name=brand_str,
                            generic_name=generic_str,
                            dosage_form=dosage_form,
                            strength=strength_str,
                            composition=clean_comp,
                            prescription_status=str(row.get("prescription_status", "prescription")).lower(),
                            source_id=source.source_id,
                            confidence_score=0.90 if source.verification_status == "verified" else 0.85,
                        )
                        session.add(med)
                        await session.flush()
                        batch_new_meds += 1

                        # Cache all keys pointing to this new medicine
                        for k in dedup_keys:
                            med_cache[k] = med
                        med_variants[med.medicine_id] = {}

                    # Pricing
                    mrp_val = _clean_price(row.get("mrp") or row.get("price"))
                    ceiling_val = _clean_price(row.get("ceiling_price"))

                    # Variant deduplication
                    var_map = med_variants.get(med.medicine_id, {})
                    var_key = (parsed_pack, parsed_unit)

                    if var_key in var_map:
                        # Variant already exists for this pack size & unit
                        batch_duplicates += 1
                        existing_var = var_map[var_key]
                        if mrp_val is not None and existing_var.mrp is None:
                            existing_var.mrp = mrp_val
                        if ceiling_val is not None and existing_var.ceiling_price is None:
                            existing_var.ceiling_price = ceiling_val
                    else:
                        # Create new MedicineVariant
                        variant = MedicineVariant(
                            medicine_id=med.medicine_id,
                            manufacturer_id=mfg_obj.manufacturer_id if mfg_obj else None,
                            pack_size=parsed_pack,
                            unit=parsed_unit,
                            packaging_description=parsed_desc or row.get("packaging_description"),
                            mrp=mrp_val,
                            ceiling_price=ceiling_val,
                            batch_number=row.get("batch_number"),
                            source_id=source.source_id,
                        )
                        session.add(variant)
                        await session.flush()
                        var_map[var_key] = variant
                        med_variants[med.medicine_id] = var_map
                        batch_variants += 1

                        # Barcode / GTIN (only if genuinely provided by source)
                        barcode_val = row.get("barcode") or row.get("ean")
                        gtin_val = row.get("gtin")

                        if barcode_val or gtin_val:
                            clean_gtin = str(gtin_val).strip() if gtin_val else None
                            clean_barcode = str(barcode_val).strip() if barcode_val else None

                            # Check unique GTIN collision
                            if clean_gtin and clean_gtin in existing_gtins:
                                clean_gtin = None

                            if clean_gtin or clean_barcode:
                                code_obj = MedicineCode(
                                    variant_id=variant.variant_id,
                                    barcode=clean_barcode,
                                    gtin=clean_gtin,
                                    source=source.source_name,
                                    verified=(source.verification_status == "verified"),
                                )
                                session.add(code_obj)
                                if clean_gtin:
                                    existing_gtins.add(clean_gtin)

                except Exception as row_err:
                    batch_failed += 1
                    err_msg = f"Row {abs_row_idx}: {str(row_err)}"
                    if len(stats.errors) < 15:
                        stats.errors.append(err_msg)

            # Commit the entire batch
            await session.commit()

            stats.imported += batch_new_meds
            stats.updated_reused += batch_reused_meds
            stats.variants_created += batch_variants
            stats.duplicate_records += batch_duplicates
            stats.skipped += batch_skipped
            stats.failed += batch_failed

            if progress_callback:
                progress_callback(batch_idx + 1, total_batches, stats)

        except Exception as batch_err:
            await session.rollback()
            batch_fail_count = len(batch)
            stats.failed += batch_fail_count
            err_msg = f"Batch {batch_idx + 1} rollback: {str(batch_err)}"
            logger.error(err_msg)
            if len(stats.errors) < 15:
                stats.errors.append(err_msg)

    # 6. Final source sync update
    try:
        source.coverage_count += stats.imported
        source.last_synced_at = datetime.now(timezone.utc)
        await session.commit()
    except Exception:
        await session.rollback()

    return stats


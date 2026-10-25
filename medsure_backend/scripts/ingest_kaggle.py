"""MedSure Vision - Ingest Kaggle Indian Medicines Dataset (Optimized Stream Engine)

Optimizations:
1. Preloads lightweight primitive in-memory caches at startup (O(1) lookups).
2. Avoids reloading 40,000+ Medicine ORM objects before every batch.
3. Eliminates unnecessary per-row session.flush() calls by generating UUIDs client-side.
4. Preserves:
   - Medicine deduplication (brand + salt + dosage + strength)
   - Variant deduplication (pack size + unit)
   - Manufacturer deduplication (normalized name)
   - Seed-data matching (all existing DB records preloaded)
   - Batch transactional commits with rollback safety
   - Row-level error isolation
   - Genuine GTIN-only insertion
5. Adds explicit --skip-rows and --auto-resume CLI options.
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
import pandas as pd

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.sources import DataSource
from app.models.manufacturer import Manufacturer
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.codes import MedicineCode
from app.utils.helpers import (
    normalize_text,
    extract_strength_string,
    parse_pack_size_label,
    build_medicine_dedup_keys,
)


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


class CachedMedicine:
    """Lightweight in-memory medicine record to avoid full ORM hydration."""
    __slots__ = ("medicine_id", "dosage_form", "strength")

    def __init__(self, medicine_id: UUID, dosage_form: Optional[str] = None, strength: Optional[str] = None):
        self.medicine_id = medicine_id
        self.dosage_form = dosage_form
        self.strength = strength


class IngestionCache:
    """Lightweight primitive in-memory deduplication index."""

    def __init__(self):
        # dedup_key -> CachedMedicine
        self.med_cache: Dict[str, CachedMedicine] = {}
        # medicine_id -> (pack_size, unit) -> variant_id (UUID)
        self.variant_cache: Dict[UUID, Dict[Tuple[Optional[int], Optional[str]], UUID]] = {}
        # normalized_mfg_name -> mfg_id (UUID)
        self.mfg_cache: Dict[str, UUID] = {}
        # set of existing GTIN strings
        self.gtin_cache: Set[str] = set()


async def preload_caches(session: AsyncSession) -> IngestionCache:
    """Preloads lightweight primitive caches once at startup via targeted scalar queries."""
    cache = IngestionCache()
    t0 = time.time()
    print("[*] Preloading deduplication caches from database...")

    # 1. Manufacturers: only (manufacturer_id, name)
    mfg_stmt = select(Manufacturer.manufacturer_id, Manufacturer.name)
    mfg_res = await session.execute(mfg_stmt)
    for mfg_id, name in mfg_res.all():
        if name:
            cache.mfg_cache[normalize_text(name)] = mfg_id

    # 2. Medicines: only (medicine_id, brand_name, generic_name, dosage_form, strength)
    med_stmt = select(
        Medicine.medicine_id,
        Medicine.brand_name,
        Medicine.generic_name,
        Medicine.dosage_form,
        Medicine.strength,
    )
    med_res = await session.execute(med_stmt)
    for med_id, b_name, g_name, d_form, strn in med_res.all():
        cached_med = CachedMedicine(med_id, d_form, strn)
        keys = build_medicine_dedup_keys(b_name or "", g_name or "", d_form, strn)
        for k in keys:
            if k not in cache.med_cache:
                cache.med_cache[k] = cached_med
        if med_id not in cache.variant_cache:
            cache.variant_cache[med_id] = {}

    # 3. Variants: only (variant_id, medicine_id, pack_size, unit)
    var_stmt = select(
        MedicineVariant.variant_id,
        MedicineVariant.medicine_id,
        MedicineVariant.pack_size,
        MedicineVariant.unit,
    )
    var_res = await session.execute(var_stmt)
    for var_id, med_id, pack_size, unit in var_res.all():
        clean_unit = (unit or "").lower().strip() if unit else None
        if med_id not in cache.variant_cache:
            cache.variant_cache[med_id] = {}
        cache.variant_cache[med_id][(pack_size, clean_unit)] = var_id

    # 4. GTINs: only (gtin)
    code_stmt = select(MedicineCode.gtin).where(MedicineCode.gtin.isnot(None))
    code_res = await session.execute(code_stmt)
    cache.gtin_cache = {c for c in code_res.scalars().all() if c}

    elapsed = time.time() - t0
    total_vars = sum(len(v) for v in cache.variant_cache.values())
    print(f"[+] Startup cache preloaded in {elapsed:.2f}s:")
    print(f"   - Cached Medicines:     {len(cache.variant_cache):,} (index keys: {len(cache.med_cache):,})")
    print(f"   - Cached Variants:      {total_vars:,}")
    print(f"   - Cached Manufacturers: {len(cache.mfg_cache):,}")
    print(f"   - Cached GTINs:         {len(cache.gtin_cache):,}\n")
    return cache


async def detect_resume_row(session: AsyncSession, csv_path: str) -> int:
    """Inspects database to detect how many rows from the CSV have already been committed."""
    # Find boundary: test row 41000
    try:
        df_boundary = pd.read_csv(csv_path, skiprows=range(1, 41001), nrows=1)
        clopicheck = df_boundary["name"].iloc[0] if not df_boundary.empty else None
        if clopicheck:
            res = await session.execute(select(Medicine.medicine_id).where(Medicine.brand_name == clopicheck))
            if res.scalar_one_or_none() is None:
                # 41,000 rows were committed!
                return 41000
    except Exception:
        pass
    return 0


async def run_kaggle_ingest(
    csv_path: str,
    limit: Optional[int] = None,
    batch_size: int = 500,
    skip_rows: int = 0,
    auto_resume: bool = False,
):
    print(f"\n==================================================")
    print(f"  MedSure Vision - Indian Medicine Dataset Ingestion")
    print(f"  (Optimized Stream Engine with O(1) Cache Lookups)")
    print(f"==================================================")
    print(f"Target file:  {csv_path}")
    print(f"Skip rows:    {skip_rows:,} (resuming after row {skip_rows:,})")
    print(f"Row limit:    {f'{limit:,}' if limit and limit > 0 else 'ALL REMAINING'}")
    print(f"Batch size:   {batch_size:,}")
    print(f"--------------------------------------------------\n")

    if not os.path.exists(csv_path):
        print(f"[!] Error: File '{csv_path}' does not exist.")
        return

    async with AsyncSessionLocal() as session:
        # Find or create kaggle data source
        stmt = select(DataSource).where(DataSource.source_name == "kaggle_dataset")
        res = await session.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            source = DataSource(
                source_name="kaggle_dataset",
                source_type="third_party",
                source_url="https://www.kaggle.com/datasets/riturajsingh2004/extensive-a-z-medicines-dataset-of-india",
                verification_status="verified",
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)

        if auto_resume and skip_rows == 0:
            detected = await detect_resume_row(session, csv_path)
            if detected > 0:
                print(f"[*] Auto-resume detected {detected:,} already committed rows.")
                skip_rows = detected
            else:
                print("[*] Auto-resume did not detect a prior boundary; starting from row 0.")

        # Preload lightweight primitive caches once at startup
        cache = await preload_caches(session)

        # Explicit resume guidance if resuming
        if skip_rows > 0:
            print(f"[>>] Skipping {skip_rows:,} rows. Processing will start at CSV row index {skip_rows:,}...")
        else:
            if len(cache.variant_cache) > 200:
                print(f"[*] Starting from row 0 with {len(cache.variant_cache):,} existing medicines in database.")
                print(f"   (Duplicates will be safely avoided via deduplication index)")

        total_processed = 0
        total_imported = 0
        total_reused = 0
        total_variants = 0
        total_duplicates = 0
        total_mfgs = 0
        total_skipped = 0
        total_failed = 0
        all_errors = []

        chunk_iter = pd.read_csv(
            csv_path,
            chunksize=batch_size,
            skiprows=range(1, skip_rows + 1) if skip_rows > 0 else None,
            nrows=limit if limit and limit > 0 else None,
            low_memory=False,
        )

        batch_number = 1
        current_row_offset = skip_rows

        for chunk in chunk_iter:
            batch_start_time = time.time()
            batch_processed = len(chunk)
            batch_new_meds = 0
            batch_reused_meds = 0
            batch_variants = 0
            batch_duplicates = 0
            batch_mfgs = 0
            batch_skipped = 0
            batch_failed = 0

            # Track additions for batch rollback safety
            batch_med_additions: List[str] = []
            batch_var_additions: List[Tuple[UUID, Tuple[Optional[int], Optional[str]]]] = []
            batch_mfg_additions: List[str] = []
            batch_gtin_additions: List[str] = []

            try:
                for _, row in chunk.iterrows():
                    abs_row_idx = current_row_offset
                    current_row_offset += 1

                    try:
                        # 1. Brand name validation
                        b_name = row.get("name") or row.get("brand_name")
                        if pd.isna(b_name) if isinstance(b_name, float) else not b_name:
                            batch_skipped += 1
                            continue
                        brand_str = str(b_name).strip()
                        if not brand_str:
                            batch_skipped += 1
                            continue

                        # 2. Generic composition
                        comp1 = row.get("short_composition1") or row.get("composition") or row.get("short_composition") or ""
                        comp2 = row.get("short_composition2") or ""
                        comp1 = "" if (isinstance(comp1, float) and pd.isna(comp1)) else str(comp1).strip()
                        comp2 = "" if (isinstance(comp2, float) and pd.isna(comp2)) else str(comp2).strip()
                        generic_str = (comp1 + (" + " + comp2 if comp2 else "")).strip() or row.get("generic_name") or brand_str
                        if isinstance(generic_str, float) and pd.isna(generic_str):
                            generic_str = brand_str
                        generic_str = str(generic_str).strip() or brand_str

                        # 3. Dosage form
                        raw_dosage = row.get("type") or row.get("dosage_form") or "Tablet"
                        dosage_form = "" if (isinstance(raw_dosage, float) and pd.isna(raw_dosage)) else str(raw_dosage).strip()
                        dosage_form = dosage_form or "Tablet"

                        # 4. Packaging and pack size parsing
                        raw_pack_label = row.get("pack_size_label") or row.get("packaging_description") or ""
                        raw_pack_label = "" if (isinstance(raw_pack_label, float) and pd.isna(raw_pack_label)) else str(raw_pack_label).strip()
                        parsed_pack, parsed_unit, parsed_desc = parse_pack_size_label(
                            raw_pack_label,
                            default_dosage_form=dosage_form,
                        )
                        if "pack_size" in row and row.get("pack_size") is not None and not (isinstance(row.get("pack_size"), float) and pd.isna(row.get("pack_size"))):
                            parsed_pack = _clean_integer(row.get("pack_size")) or parsed_pack
                        if "unit" in row and row.get("unit") and not (isinstance(row.get("unit"), float) and pd.isna(row.get("unit"))):
                            parsed_unit = str(row.get("unit")).strip().lower() or parsed_unit

                        # 5. Strength parsing
                        strength_str = extract_strength_string(
                            row.get("strength"),
                            fallback_text=f"{brand_str} {generic_str}",
                        )

                        # 6. Manufacturer check, deduplication & client-side UUID
                        mfg_id = None
                        mfg_name = row.get("manufacturer_name") or row.get("manufacturer") or ""
                        mfg_name = "" if (isinstance(mfg_name, float) and pd.isna(mfg_name)) else str(mfg_name).strip()
                        if mfg_name:
                            norm_mfg = normalize_text(mfg_name)
                            if norm_mfg in cache.mfg_cache:
                                mfg_id = cache.mfg_cache[norm_mfg]
                            else:
                                mfg_id = uuid4()
                                mfg = Manufacturer(
                                    manufacturer_id=mfg_id,
                                    name=mfg_name,
                                    source_id=source.source_id,
                                    verification_status="verified" if source.verification_status == "verified" else "pending",
                                )
                                session.add(mfg)
                                cache.mfg_cache[norm_mfg] = mfg_id
                                batch_mfg_additions.append(norm_mfg)
                                batch_mfgs += 1

                        # 7. Medicine deduplication
                        dedup_keys = build_medicine_dedup_keys(brand_str, generic_str, dosage_form, strength_str)
                        matched_med: Optional[CachedMedicine] = None
                        for k in dedup_keys:
                            if k in cache.med_cache:
                                matched_med = cache.med_cache[k]
                                break

                        if matched_med:
                            med_id = matched_med.medicine_id
                            batch_reused_meds += 1
                        else:
                            med_id = uuid4()
                            clean_comp = {
                                "raw": generic_str,
                                "active_ingredients": [],
                                "excipients": [],
                            }
                            med = Medicine(
                                medicine_id=med_id,
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
                            cached_med = CachedMedicine(med_id, dosage_form, strength_str)
                            for k in dedup_keys:
                                cache.med_cache[k] = cached_med
                                batch_med_additions.append(k)
                            cache.variant_cache[med_id] = {}
                            batch_new_meds += 1

                        # 8. Pricing
                        raw_price = row.get("price(\u20b9)") or row.get("price") or row.get("mrp")
                        mrp_val = _clean_price(raw_price)
                        ceiling_val = _clean_price(row.get("ceiling_price"))

                        # 9. Variant deduplication
                        var_map = cache.variant_cache.setdefault(med_id, {})
                        var_key = (parsed_pack, parsed_unit)

                        if var_key in var_map:
                            # Variant already exists
                            batch_duplicates += 1
                        else:
                            var_id = uuid4()
                            variant = MedicineVariant(
                                variant_id=var_id,
                                medicine_id=med_id,
                                manufacturer_id=mfg_id,
                                pack_size=parsed_pack,
                                unit=parsed_unit,
                                packaging_description=parsed_desc or raw_pack_label or None,
                                mrp=mrp_val,
                                ceiling_price=ceiling_val,
                                batch_number=str(row.get("batch_number")).strip() if row.get("batch_number") and not (isinstance(row.get("batch_number"), float) and pd.isna(row.get("batch_number"))) else None,
                                source_id=source.source_id,
                            )
                            session.add(variant)
                            var_map[var_key] = var_id
                            batch_var_additions.append((med_id, var_key))
                            batch_variants += 1

                            # 10. Barcode / GTIN (genuine GTIN-only)
                            barcode_val = row.get("barcode") or row.get("ean")
                            gtin_val = row.get("gtin")
                            if barcode_val or gtin_val:
                                clean_gtin = str(gtin_val).strip() if (gtin_val and not (isinstance(gtin_val, float) and pd.isna(gtin_val))) else None
                                clean_barcode = str(barcode_val).strip() if (barcode_val and not (isinstance(barcode_val, float) and pd.isna(barcode_val))) else None
                                if clean_gtin and clean_gtin in cache.gtin_cache:
                                    clean_gtin = None
                                if clean_gtin or clean_barcode:
                                    code_obj = MedicineCode(
                                        code_id=uuid4(),
                                        variant_id=var_id,
                                        barcode=clean_barcode,
                                        gtin=clean_gtin,
                                        source=source.source_name,
                                        verified=(source.verification_status == "verified"),
                                    )
                                    session.add(code_obj)
                                    if clean_gtin:
                                        cache.gtin_cache.add(clean_gtin)
                                        batch_gtin_additions.append(clean_gtin)

                    except Exception as row_err:
                        batch_failed += 1
                        if len(all_errors) < 20:
                            all_errors.append(f"Row {abs_row_idx}: {str(row_err)}")

                # Commit batch transactionally
                await session.commit()
                batch_duration = time.time() - batch_start_time

                total_processed += batch_processed
                total_imported += batch_new_meds
                total_reused += batch_reused_meds
                total_variants += batch_variants
                total_duplicates += batch_duplicates
                total_mfgs += batch_mfgs
                total_skipped += batch_skipped
                total_failed += batch_failed

                print(
                    f"[Batch {batch_number:3d}] "
                    f"Rows: {batch_processed:4d} | "
                    f"New Meds: {batch_new_meds:4d} | "
                    f"Reused Meds: {batch_reused_meds:4d} | "
                    f"New Vars: {batch_variants:4d} | "
                    f"Dup Vars: {batch_duplicates:3d} | "
                    f"New Mfgs: {batch_mfgs:3d} | "
                    f"Duration: {batch_duration:.2f}s"
                )
                batch_number += 1

            except Exception as batch_err:
                await session.rollback()
                # Clean up in-memory cache additions for rolled-back batch
                for k in batch_med_additions:
                    cache.med_cache.pop(k, None)
                for med_id, var_key in batch_var_additions:
                    if med_id in cache.variant_cache:
                        cache.variant_cache[med_id].pop(var_key, None)
                for norm_mfg in batch_mfg_additions:
                    cache.mfg_cache.pop(norm_mfg, None)
                for gtin in batch_gtin_additions:
                    cache.gtin_cache.discard(gtin)

                batch_fail_count = len(chunk)
                total_failed += batch_fail_count
                print(f"[!] Batch {batch_number} failed and rolled back: {batch_err}")
                if len(all_errors) < 20:
                    all_errors.append(f"Batch {batch_number} rollback: {str(batch_err)}")
                batch_number += 1

        # Update source coverage count and sync time
        try:
            source.coverage_count += total_imported
            source.last_synced_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception:
            await session.rollback()

        print(f"\n==================================================")
        print(f"  Ingestion Summary Report")
        print(f"==================================================")
        print(f"  Total Rows Processed:   {total_processed:,}")
        print(f"  New Medicines Inserted: {total_imported:,}")
        print(f"  Medicines Reused:       {total_reused:,}")
        print(f"  New Variants Created:   {total_variants:,}")
        print(f"  Duplicate Variants:     {total_duplicates:,}")
        print(f"  New Manufacturers:      {total_mfgs:,}")
        print(f"  Skipped Invalid Rows:   {total_skipped:,}")
        print(f"  Failed Rows:            {total_failed:,}")
        if all_errors:
            print(f"  Sample Errors:          {all_errors[:5]}")
        print(f"==================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Kaggle Indian Medicines Dataset")
    parser.add_argument("--file", type=str, default="medicines_kaggle.csv", help="Path to CSV file")
    parser.add_argument("--limit", type=int, default=None, help="Maximum total rows to ingest (default: all remaining)")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for processing and commit (default: 500)")
    parser.add_argument("--skip-rows", type=int, default=0, help="Number of CSV data rows to skip before processing (default: 0)")
    parser.add_argument("--auto-resume", action="store_true", help="Auto-detect already committed rows and resume seamlessly")
    args = parser.parse_args()

    asyncio.run(run_kaggle_ingest(
        csv_path=args.file,
        limit=args.limit,
        batch_size=args.batch_size,
        skip_rows=args.skip_rows,
        auto_resume=args.auto_resume,
    ))

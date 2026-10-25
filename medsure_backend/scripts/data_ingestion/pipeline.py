"""pipeline.py - Orchestrated, idempotent data ingestion pipeline for MedSure Vision.

Executes official source importers (PMBI, NPPA, CDSCO), enforces deduplication,
preserves provenance, tracks execution runs in data_import_run, and updates
catalogue statistics.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sources import DataSource
from app.models.manufacturer import Manufacturer
from app.models.medicine import MedicineMaster
from app.models.variant import MedicineVariant
from app.models.codes import MedicineIdentifier
from app.models.price import MedicinePrice
from app.models.alerts import RegulatoryAlert
from app.models.import_run import DataImportRun

from scripts.data_ingestion.base import (
    BaseSourceImporter,
    ImportStats,
    RawMedicineRecord,
    RawRegulatoryAlert,
)
from scripts.data_ingestion.deduplicator import compute_medicine_hash, compute_variant_hash
from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_strength,
    normalize_dosage_form,
    normalize_manufacturer,
    normalize_pack_size,
    normalize_mrp,
)


class DataIngestionPipeline:
    """Idempotent ingestion pipeline for all authoritative source adapters."""

    async def run_adapter(
        self,
        session: AsyncSession,
        adapter: BaseSourceImporter,
    ) -> ImportStats:
        """Executes an adapter run within an async database transaction."""
        stats = ImportStats(
            source_name=adapter.source_name,
            adapter_name=adapter.__class__.__name__,
        )

        now = datetime.now(timezone.utc)

        # 1. Ensure DataSource record exists
        src_stmt = select(DataSource).where(DataSource.source_name == adapter.source_name)
        src_res = await session.execute(src_stmt)
        data_source = src_res.scalar_one_or_none()
        if not data_source:
            data_source = DataSource(
                source_name=adapter.source_name,
                source_type=adapter.source_type,
                source_url=adapter.source_url,
                verification_status="verified",
                coverage_count=0,
            )
            session.add(data_source)
            await session.flush()

        # 2. Create DataImportRun tracking record
        import_run = DataImportRun(
            source_name=adapter.source_name,
            adapter_name=adapter.__class__.__name__,
            status="running",
            started_at=now,
            source_url_or_file=adapter.source_url,
        )
        session.add(import_run)
        await session.flush()

        try:
            # 3. Check if adapter has medicine records or regulatory alerts
            if hasattr(adapter, "load_alert_records"):
                alert_records: List[RawRegulatoryAlert] = await adapter.load_alert_records()
                await self._process_alerts(session, data_source, alert_records, stats)
            else:
                med_records: List[RawMedicineRecord] = await adapter.load_records()
                await self._process_medicines(session, data_source, med_records, stats)

            # 4. Update data_source coverage
            count_stmt = select(func.count(MedicineMaster.medicine_id)).where(
                MedicineMaster.source_id == data_source.source_id
            )
            total_items = (await session.execute(count_stmt)).scalar() or 0
            if total_items == 0:
                # Count alerts if it's an alert source
                alert_count_stmt = select(func.count(RegulatoryAlert.alert_id)).where(
                    RegulatoryAlert.source_id == data_source.source_id
                )
                total_items = (await session.execute(alert_count_stmt)).scalar() or 0

            data_source.coverage_count = total_items
            data_source.last_synced_at = datetime.now(timezone.utc)

            # 5. Finalize DataImportRun
            import_run.status = "completed"
            import_run.completed_at = datetime.now(timezone.utc)
            import_run.records_read = stats.records_read
            import_run.records_imported = stats.records_imported
            import_run.records_updated = stats.records_updated
            import_run.records_skipped = stats.records_skipped
            import_run.errors_count = stats.errors_count
            if stats.error_summary:
                import_run.error_summary = "\n".join(stats.error_summary[:10])

            await session.commit()
            stats.status = "completed"

        except Exception as exc:
            await session.rollback()
            stats.status = "failed"
            stats.errors_count += 1
            stats.error_summary.append(str(exc))

            # Record failure in separate transaction
            try:
                import_run.status = "failed"
                import_run.completed_at = datetime.now(timezone.utc)
                import_run.error_summary = str(exc)
                session.add(import_run)
                await session.commit()
            except Exception:
                pass
            raise exc

        return stats

    async def _process_medicines(
        self,
        session: AsyncSession,
        data_source: DataSource,
        records: List[RawMedicineRecord],
        stats: ImportStats,
    ):
        """Processes and deduplicates raw medicine records."""
        now = datetime.now(timezone.utc)
        stats.records_read = len(records)

        # Cache existing manufacturers
        mfg_cache: Dict[str, Manufacturer] = {}
        all_mfgs = (await session.execute(select(Manufacturer))).scalars().all()
        for m in all_mfgs:
            mfg_cache[m.name.lower().strip()] = m

        for rec in records:
            try:
                brand_clean = normalize_brand_name(rec.brand_name)
                generic_clean = normalize_generic_name(rec.generic_name)
                strength_clean = normalize_strength(rec.strength)
                dosage_clean = normalize_dosage_form(rec.dosage_form)

                med_hash = compute_medicine_hash(
                    brand_clean, generic_clean, strength_clean, dosage_clean
                )

                # Query existing medicine by hash or source_record_id
                existing_stmt = select(MedicineMaster).where(
                    (MedicineMaster.normalization_hash == med_hash)
                    | (
                        (MedicineMaster.source_name == data_source.source_name)
                        & (MedicineMaster.source_record_id == rec.provenance.source_record_id)
                        & (MedicineMaster.source_record_id.isnot(None))
                    )
                )
                existing_med = (await session.execute(existing_stmt)).scalars().first()

                if not existing_med:
                    # New master formulation
                    new_med = MedicineMaster(
                        brand_name=brand_clean,
                        generic_name=generic_clean,
                        dosage_form=dosage_clean,
                        strength=strength_clean,
                        composition=rec.composition,
                        therapeutic_category=rec.therapeutic_category,
                        prescription_status=rec.prescription_status,
                        confidence_score=rec.confidence_score,
                        source_id=data_source.source_id,
                        source_name=data_source.source_name,
                        source_url=data_source.source_url,
                        source_record_id=rec.provenance.source_record_id if rec.provenance else None,
                        retrieval_date=now,
                        source_updated_at=now,
                        last_verified_at=now,
                        is_demo=False,
                        normalization_hash=med_hash,
                    )
                    session.add(new_med)
                    await session.flush()
                    medicine = new_med
                    stats.records_imported += 1
                else:
                    # Preserve provenance without blind overwrite
                    medicine = existing_med
                    medicine.last_verified_at = now
                    # Enrich missing values only
                    if not medicine.therapeutic_category and rec.therapeutic_category:
                        medicine.therapeutic_category = rec.therapeutic_category
                    if not medicine.strength and strength_clean:
                        medicine.strength = strength_clean
                    stats.records_skipped += 1

                # Manufacturer handling
                manufacturer = None
                if rec.manufacturer_name and str(rec.manufacturer_name).strip():
                    mfg_name_clean = normalize_manufacturer(rec.manufacturer_name)
                    mfg_key = mfg_name_clean.lower().strip()
                    if mfg_key not in mfg_cache:
                        new_mfg = Manufacturer(
                            name=mfg_name_clean,
                            raw_name=rec.manufacturer_name,
                            address=rec.manufacturer_address,
                            verification_status="verified" if data_source.source_type == "government" else "pending",
                            source_id=data_source.source_id,
                            source_name=data_source.source_name,
                            source_url=data_source.source_url,
                            retrieval_date=now,
                            last_verified_at=now,
                            is_demo=False,
                        )
                        session.add(new_mfg)
                        await session.flush()
                        mfg_cache[mfg_key] = new_mfg
                    manufacturer = mfg_cache[mfg_key]

                # Variant handling
                pack_size, pack_unit = normalize_pack_size(rec.pack_size, rec.unit)
                var_hash = compute_variant_hash(
                    str(medicine.medicine_id),
                    manufacturer.name if manufacturer else None,
                    pack_size,
                    pack_unit,
                )

                var_stmt = select(MedicineVariant).where(
                    (MedicineVariant.variant_hash == var_hash)
                    | (
                        (MedicineVariant.medicine_id == medicine.medicine_id)
                        & (MedicineVariant.pack_size == pack_size)
                        & (MedicineVariant.unit == pack_unit)
                    )
                )
                variant = (await session.execute(var_stmt)).scalars().first()

                if not variant:
                    new_var = MedicineVariant(
                        medicine_id=medicine.medicine_id,
                        manufacturer_id=manufacturer.manufacturer_id if manufacturer else None,
                        pack_size=pack_size,
                        unit=pack_unit,
                        packaging_description=rec.packaging_description or f"Pack of {pack_size} {pack_unit}s",
                        mrp=rec.mrp,
                        ceiling_price=rec.ceiling_price,
                        source_id=data_source.source_id,
                        source_name=data_source.source_name,
                        source_url=data_source.source_url,
                        source_record_id=rec.provenance.source_record_id if rec.provenance else None,
                        retrieval_date=now,
                        last_verified_at=now,
                        is_demo=False,
                        variant_hash=var_hash,
                    )
                    session.add(new_var)
                    await session.flush()
                    variant = new_var
                else:
                    # Enrich price provenance
                    variant.last_verified_at = now
                    if rec.ceiling_price and not variant.ceiling_price:
                        variant.ceiling_price = rec.ceiling_price
                    if rec.mrp and not variant.mrp:
                        variant.mrp = rec.mrp

                # Identifier handling (do not invent barcodes)
                id_val = rec.identifier_value or rec.barcode or rec.gtin
                id_type = rec.identifier_type or ("gtin" if rec.gtin else "barcode" if rec.barcode else None)
                if id_val and id_type:
                    id_stmt = select(MedicineIdentifier).where(
                        (MedicineIdentifier.variant_id == variant.variant_id)
                        & (MedicineIdentifier.identifier_type == id_type)
                        & (MedicineIdentifier.identifier_value == id_val)
                    )
                    ident = (await session.execute(id_stmt)).scalars().first()
                    if not ident:
                        new_ident = MedicineIdentifier(
                            variant_id=variant.variant_id,
                            identifier_type=id_type,
                            identifier_value=id_val,
                            gtin=rec.gtin,
                            barcode=rec.barcode,
                            source_name=data_source.source_name,
                            source_url=data_source.source_url,
                            source_record_id=rec.provenance.source_record_id if rec.provenance else None,
                            retrieval_date=now,
                            verified=True,
                            is_demo=False,
                        )
                        session.add(new_ident)

                # Price tracking (dedicated medicine_price entry)
                if rec.mrp or rec.ceiling_price:
                    p_type = "ceiling_price" if rec.ceiling_price else "mrp"
                    p_amt = rec.ceiling_price if rec.ceiling_price else rec.mrp
                    price_stmt = select(MedicinePrice).where(
                        (MedicinePrice.variant_id == variant.variant_id)
                        & (MedicinePrice.price_type == p_type)
                        & (MedicinePrice.source_name == data_source.source_name)
                    )
                    price_rec = (await session.execute(price_stmt)).scalars().first()
                    if not price_rec and p_amt:
                        new_price = MedicinePrice(
                            variant_id=variant.variant_id,
                            price_type=p_type,
                            amount=p_amt,
                            currency="INR",
                            unit=f"1 Pack ({pack_size} {pack_unit}s)",
                            pack_size=pack_size,
                            source_name=data_source.source_name,
                            source_url=data_source.source_url,
                            source_record_id=rec.provenance.source_record_id if rec.provenance else None,
                            retrieval_date=now,
                            is_current=True,
                            is_demo=False,
                        )
                        session.add(new_price)

            except Exception as item_err:
                stats.errors_count += 1
                stats.error_summary.append(f"Failed item {rec.brand_name}: {str(item_err)}")

    async def _process_alerts(
        self,
        session: AsyncSession,
        data_source: DataSource,
        records: List[RawRegulatoryAlert],
        stats: ImportStats,
    ):
        """Processes and deduplicates official regulatory alert notices."""
        now = datetime.now(timezone.utc)
        stats.records_read = len(records)

        for alert in records:
            try:
                # Deduplication by batch_number and source_record_id
                stmt = select(RegulatoryAlert).where(
                    (RegulatoryAlert.batch_number == alert.batch_number)
                    & (RegulatoryAlert.source_name == data_source.source_name)
                )
                existing = (await session.execute(stmt)).scalars().first()

                if not existing:
                    # Attempt linking to existing medicine formulation by generic or brand
                    med_match = None
                    if alert.generic_name:
                        m_stmt = select(MedicineMaster).where(
                            func.lower(MedicineMaster.generic_name).contains(alert.generic_name.lower())
                        )
                        med_match = (await session.execute(m_stmt)).scalars().first()

                    new_alert = RegulatoryAlert(
                        medicine_id=med_match.medicine_id if med_match else None,
                        alert_type=alert.alert_type,
                        batch_number=alert.batch_number,
                        manufacturer=alert.manufacturer_name,
                        alert_date=alert.alert_date,
                        source_url=alert.source_url or data_source.source_url,
                        description=alert.description,
                        reason_for_nsq=alert.reason_for_nsq,
                        testing_lab=alert.testing_lab,
                        severity=alert.severity,
                        is_active=True,
                        source_id=data_source.source_id,
                        source_name=data_source.source_name,
                        source_record_id=alert.source_record_id,
                        retrieval_date=now,
                        last_verified_at=now,
                        is_demo=False,
                        is_fixture=alert.is_fixture,
                    )
                    session.add(new_alert)
                    stats.records_imported += 1
                else:
                    existing.last_verified_at = now
                    stats.records_skipped += 1

            except Exception as alert_err:
                stats.errors_count += 1
                stats.error_summary.append(f"Failed alert {alert.batch_number}: {str(alert_err)}")

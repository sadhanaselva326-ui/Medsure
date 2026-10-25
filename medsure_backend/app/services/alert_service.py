from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alerts import RegulatoryAlert
from app.models.medicine import Medicine
from app.schemas.alerts import RegulatoryAlertRead


async def get_alerts_for_medicine_or_batch(
    session: AsyncSession,
    medicine_id: Optional[UUID] = None,
    variant_id: Optional[UUID] = None,
    batch_number: Optional[str] = None,
    manufacturer: Optional[str] = None,
    active_only: bool = True,
    for_scan: bool = False,
) -> List[RegulatoryAlertRead]:
    """Retrieve regulatory alerts matching medicine ID, variant, batch, or manufacturer."""
    clean_batch = batch_number.strip() if batch_number else None
    clean_mfg = manufacturer.strip() if manufacturer else None

    if for_scan:
        conditions = []
        med_conds = []
        if medicine_id:
            med_conds.append(RegulatoryAlert.medicine_id == medicine_id)
        if variant_id:
            med_conds.append(RegulatoryAlert.variant_id == variant_id)

        # 1. Product-wide alerts on this medicine or variant (batch_number is NULL or empty)
        if med_conds:
            conditions.append(
                and_(
                    or_(*med_conds),
                    or_(RegulatoryAlert.batch_number.is_(None), RegulatoryAlert.batch_number == ""),
                )
            )

        # 2. Batch-specific alerts (if scanned batch is provided)
        if clean_batch:
            batch_match = func.lower(func.trim(RegulatoryAlert.batch_number)) == clean_batch.lower()
            if med_conds:
                conditions.append(
                    and_(
                        batch_match,
                        or_(*med_conds, RegulatoryAlert.medicine_id.is_(None)),
                    )
                )
            else:
                conditions.append(batch_match)

        # 3. Manufacturer-wide alerts (without specific batch or medicine)
        if clean_mfg and not med_conds and not clean_batch:
            conditions.append(
                and_(
                    RegulatoryAlert.manufacturer.ilike(f"%{clean_mfg}%"),
                    or_(RegulatoryAlert.batch_number.is_(None), RegulatoryAlert.batch_number == ""),
                    RegulatoryAlert.medicine_id.is_(None),
                )
            )

        if not conditions:
            return []

        stmt = (
            select(RegulatoryAlert)
            .options(selectinload(RegulatoryAlert.medicine))
            .where(or_(*conditions))
        )
    else:
        conditions = []

        if medicine_id:
            conditions.append(RegulatoryAlert.medicine_id == medicine_id)
        if variant_id:
            conditions.append(RegulatoryAlert.variant_id == variant_id)
        if clean_batch:
            conditions.append(
                func.lower(func.trim(RegulatoryAlert.batch_number)) == clean_batch.lower()
            )
        if clean_mfg:
            conditions.append(
                RegulatoryAlert.manufacturer.ilike(f"%{clean_mfg}%")
            )

        if not conditions:
            return []

        stmt = (
            select(RegulatoryAlert)
            .options(selectinload(RegulatoryAlert.medicine))
            .where(or_(*conditions))
        )

    if active_only:
        stmt = stmt.where(RegulatoryAlert.is_active == True)

    stmt = stmt.order_by(RegulatoryAlert.alert_date.desc())
    result = await session.execute(stmt)
    alerts = result.scalars().all()

    alert_reads = []
    for alert in alerts:
        alert_reads.append(
            RegulatoryAlertRead(
                alert_id=alert.alert_id,
                alert_type=alert.alert_type,
                batch_number=alert.batch_number,
                manufacturer=alert.manufacturer,
                alert_date=str(alert.alert_date),
                source_url=alert.source_url,
                description=alert.description,
                is_active=alert.is_active,
                medicine_id=alert.medicine_id,
                variant_id=alert.variant_id,
                source_id=alert.source_id,
                created_at=alert.created_at,
                imported_at=alert.imported_at,
                internal_ref=alert.source_record_id,
                risk_rating=getattr(alert, 'risk_rating', None),
                drug_name=alert.drug_name,
                reason_for_nsq=getattr(alert, 'reason_for_nsq', None),
                testing_lab=getattr(alert, 'testing_lab', None),
                mfg_date=getattr(alert, 'mfg_date', None),
                exp_date=getattr(alert, 'exp_date', None),
                notice_month=getattr(alert, 'notice_month', None),
                source_file_name=getattr(alert, 'source_file_name', None),
                source_file_hash=getattr(alert, 'source_file_hash', None),
                page_number=getattr(alert, 'page_number', None),
                s_no_in_pdf=getattr(alert, 's_no_in_pdf', None),
                row_index_on_page=getattr(alert, 'row_index_on_page', None),
                row_number=getattr(alert, 'row_number', None),
                is_state=getattr(alert, 'is_state', None),
                licence_note=getattr(alert, 'licence_note', None),
                source_record_id=alert.source_record_id,
                brand_name=alert.medicine.brand_name if alert.medicine else None,
                generic_name=alert.medicine.generic_name if alert.medicine else None,
            )
        )

    return alert_reads

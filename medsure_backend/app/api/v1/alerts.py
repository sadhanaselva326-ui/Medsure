import math
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.alerts import RegulatoryAlert
from app.schemas.alerts import RegulatoryAlertRead
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services.alert_service import get_alerts_for_medicine_or_batch

router = APIRouter(prefix="/alerts", tags=["Regulatory Alerts"])


@router.get("", response_model=PaginatedResponse[RegulatoryAlertRead])
async def list_regulatory_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="critical, high, medium, low"),
    alert_type: Optional[str] = Query(None, description="recall, advisory, quality_alert, batch_alert, price_violation"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all regulatory alerts with optional filtering by severity, type, and active status."""
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit

    stmt = select(RegulatoryAlert).options(selectinload(RegulatoryAlert.medicine))
    filters = []

    if severity:
        filters.append(func.lower(RegulatoryAlert.severity) == severity.strip().lower())
    if alert_type:
        filters.append(func.lower(RegulatoryAlert.alert_type) == alert_type.strip().lower())
    if is_active is not None:
        filters.append(RegulatoryAlert.is_active == is_active)

    if filters:
        stmt = stmt.where(and_(*filters))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(RegulatoryAlert.alert_date.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    alert_reads = [
        RegulatoryAlertRead(
            alert_id=a.alert_id,
            alert_type=a.alert_type,
            batch_number=a.batch_number,
            manufacturer=a.manufacturer,
            alert_date=str(a.alert_date),  # always a str; str() guards against any legacy date objects
            source_url=a.source_url,
            description=a.description,
            is_active=a.is_active,
            medicine_id=a.medicine_id,
            variant_id=a.variant_id,
            source_id=a.source_id,
            created_at=a.created_at,
            imported_at=a.imported_at,
            internal_ref=a.source_record_id,
            risk_rating=getattr(a, 'risk_rating', None),
            drug_name=a.drug_name,
            reason_for_nsq=getattr(a, 'reason_for_nsq', None),
            testing_lab=getattr(a, 'testing_lab', None),
            mfg_date=getattr(a, 'mfg_date', None),
            exp_date=getattr(a, 'exp_date', None),
            notice_month=getattr(a, 'notice_month', None),
            source_file_name=getattr(a, 'source_file_name', None),
            source_file_hash=getattr(a, 'source_file_hash', None),
            page_number=getattr(a, 'page_number', None),
            s_no_in_pdf=getattr(a, 's_no_in_pdf', None),
            row_index_on_page=getattr(a, 'row_index_on_page', None),
            row_number=getattr(a, 'row_number', None),
            is_state=getattr(a, 'is_state', None),
            licence_note=getattr(a, 'licence_note', None),
            source_record_id=a.source_record_id,
            brand_name=a.medicine.brand_name if a.medicine else None,
            generic_name=a.medicine.generic_name if a.medicine else None,
        )
        for a in alerts
    ]

    total_pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedResponse(
        data=alert_reads,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/batch/{batch_number}", response_model=List[RegulatoryAlertRead])
async def get_alerts_by_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Check regulatory recalls and quality alerts by batch number."""
    return await get_alerts_for_medicine_or_batch(
        session=db,
        batch_number=batch_number,
        active_only=False,
    )


@router.get("/{medicine_id}", response_model=List[RegulatoryAlertRead])
async def get_alerts_for_medicine(
    medicine_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all regulatory alerts associated with a specific medicine."""
    return await get_alerts_for_medicine_or_batch(
        session=db,
        medicine_id=medicine_id,
        active_only=False,
    )

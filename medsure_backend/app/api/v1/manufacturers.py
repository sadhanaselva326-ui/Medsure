import math
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.manufacturer import Manufacturer
from app.models.variant import MedicineVariant
from app.models.medicine import Medicine
from app.schemas.manufacturer import (
    ManufacturerRead,
    ManufacturerDetailRead,
    ManufacturerMedicineItem,
)
from app.schemas.common import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/manufacturers", tags=["Manufacturers"])


@router.get("/search", response_model=PaginatedResponse[ManufacturerRead])
async def search_manufacturers(
    q: Optional[str] = Query(None, description="Search term for manufacturer name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Search registered pharmaceutical manufacturers by name with trigram similarity."""
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit

    stmt = select(Manufacturer)
    if q and q.strip():
        search_term = q.strip()
        stmt = stmt.where(Manufacturer.name.ilike(f"%{search_term}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(Manufacturer.name.asc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    manufacturers = result.scalars().all()

    total_pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedResponse(
        data=manufacturers,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/{manufacturer_id}", response_model=ManufacturerDetailRead)
async def get_manufacturer_details(
    manufacturer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get manufacturer details along with all medicines manufactured."""
    stmt = (
        select(Manufacturer)
        .options(
            selectinload(Manufacturer.variants)
            .selectinload(MedicineVariant.medicine)
        )
        .where(Manufacturer.manufacturer_id == manufacturer_id)
    )
    result = await db.execute(stmt)
    mfg = result.scalars().first()

    if not mfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with ID '{manufacturer_id}' not found.",
        )

    # Deduplicate medicines produced
    seen_ids = set()
    med_items: List[ManufacturerMedicineItem] = []
    for v in mfg.variants:
        if v.medicine and v.medicine.medicine_id not in seen_ids:
            seen_ids.add(v.medicine.medicine_id)
            med_items.append(
                ManufacturerMedicineItem(
                    medicine_id=v.medicine.medicine_id,
                    brand_name=v.medicine.brand_name,
                    generic_name=v.medicine.generic_name,
                    strength=v.medicine.strength,
                    dosage_form=v.medicine.dosage_form,
                )
            )

    return ManufacturerDetailRead(
        manufacturer_id=mfg.manufacturer_id,
        name=mfg.name,
        address=mfg.address,
        gstin=mfg.gstin,
        verification_status=mfg.verification_status,
        source_id=mfg.source_id,
        created_at=mfg.created_at,
        updated_at=mfg.updated_at,
        medicines=med_items,
    )

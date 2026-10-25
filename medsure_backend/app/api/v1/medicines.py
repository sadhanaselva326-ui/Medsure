import math
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.codes import MedicineCode
from app.models.images import MedicineImage
from app.models.substitutes import MedicineSubstitute
from app.models.alerts import RegulatoryAlert
from app.schemas.medicine import (
    MedicineDetailRead,
    MedicineSearchResultItem,
    SubstituteItem,
)
from app.schemas.variant import MedicineVariantRead, MedicineImageRead
from app.schemas.common import PaginatedResponse
from app.services.search_service import search_medicines

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.get("/search", response_model=PaginatedResponse[MedicineSearchResultItem])
async def search_medicines_endpoint(
    q: Optional[str] = Query(None, description="Search keyword for brand name, generic name, composition"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    dosage_form: Optional[str] = Query(None, description="Filter by dosage form (e.g., Tablet, Syrup)"),
    strength: Optional[str] = Query(None, description="Filter by strength (e.g., 650mg, 500mg)"),
    prescription_status: Optional[str] = Query(None, description="Filter by status: prescription, otc, restricted"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer name"),
    db: AsyncSession = Depends(get_db),
):
    """Search medicines across brand name, generic name, and composition using

    PostgreSQL Full-Text Search (tsvector) with trigram similarity fallback.
    """
    return await search_medicines(
        session=db,
        query=q,
        page=page,
        limit=limit,
        dosage_form=dosage_form,
        strength=strength,
        prescription_status=prescription_status,
        manufacturer_name=manufacturer,
    )


@router.get("/by-code/{gtin}", response_model=MedicineDetailRead)
async def get_medicine_by_gtin_or_barcode(
    gtin: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup medicine record by its 14-digit GTIN or 13-digit EAN barcode."""
    code_clean = gtin.strip()

    stmt = (
        select(MedicineCode)
        .options(
            selectinload(MedicineCode.variant)
            .selectinload(MedicineVariant.medicine)
            .selectinload(Medicine.source),
            selectinload(MedicineCode.variant)
            .selectinload(MedicineVariant.medicine)
            .selectinload(Medicine.variants)
            .selectinload(MedicineVariant.codes),
            selectinload(MedicineCode.variant)
            .selectinload(MedicineVariant.medicine)
            .selectinload(Medicine.variants)
            .selectinload(MedicineVariant.images),
            selectinload(MedicineCode.variant)
            .selectinload(MedicineVariant.medicine)
            .selectinload(Medicine.variants)
            .selectinload(MedicineVariant.manufacturer),
        )
        .where(
            or_(
                MedicineCode.gtin == code_clean,
                MedicineCode.barcode == code_clean,
                MedicineCode.identifier_value == code_clean,
            )
        )
    )
    result = await db.execute(stmt)
    code_record = result.scalars().first()

    if not code_record or not code_record.variant or not code_record.variant.medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No medicine found with barcode/GTIN '{code_clean}'.",
        )

    med = code_record.variant.medicine
    return await _format_medicine_detail(db, med)


@router.get("/{medicine_id}", response_model=MedicineDetailRead)
async def get_medicine_by_id(
    medicine_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full medicine details including variants, images, source provenance,

    confidence score, and therapeutic substitutes.
    """
    stmt = (
        select(Medicine)
        .options(
            selectinload(Medicine.source),
            selectinload(Medicine.variants).selectinload(MedicineVariant.manufacturer),
            selectinload(Medicine.variants).selectinload(MedicineVariant.codes),
            selectinload(Medicine.variants).selectinload(MedicineVariant.images),
        )
        .where(Medicine.medicine_id == medicine_id)
    )
    result = await db.execute(stmt)
    med = result.scalars().first()

    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID '{medicine_id}' not found.",
        )

    return await _format_medicine_detail(db, med)


@router.get("/{id}/variants", response_model=List[MedicineVariantRead])
async def get_medicine_variants(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all packaging and pricing variants for a specific medicine."""
    stmt = (
        select(MedicineVariant)
        .options(
            selectinload(MedicineVariant.manufacturer),
            selectinload(MedicineVariant.codes),
            selectinload(MedicineVariant.images),
        )
        .where(MedicineVariant.medicine_id == id)
    )
    result = await db.execute(stmt)
    variants = result.scalars().all()

    output = []
    for v in variants:
        output.append(
            MedicineVariantRead(
                variant_id=v.variant_id,
                medicine_id=v.medicine_id,
                manufacturer_id=v.manufacturer_id,
                manufacturer_name=v.manufacturer.name if v.manufacturer else None,
                pack_size=v.pack_size,
                unit=v.unit,
                packaging_description=v.packaging_description,
                mrp=float(v.mrp) if v.mrp is not None else None,
                ceiling_price=float(v.ceiling_price) if v.ceiling_price is not None else None,
                batch_number=v.batch_number,
                expiry_date=v.expiry_date,
                source_id=v.source_id,
                created_at=v.created_at,
                updated_at=v.updated_at,
                codes=v.codes,
                images=v.images,
            )
        )
    return output


@router.get("/{id}/images", response_model=List[MedicineImageRead])
async def get_medicine_images(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all reference packaging images for a specific medicine."""
    stmt = (
        select(MedicineImage)
        .join(MedicineVariant)
        .where(MedicineVariant.medicine_id == id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{id}/substitutes", response_model=List[SubstituteItem])
async def get_medicine_substitutes(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get therapeutic substitutes with similarity scores based on active chemical composition."""
    stmt = (
        select(MedicineSubstitute)
        .options(
            selectinload(MedicineSubstitute.substitute_medicine)
            .selectinload(Medicine.variants)
            .selectinload(MedicineVariant.manufacturer)
        )
        .where(MedicineSubstitute.medicine_id == id)
        .order_by(MedicineSubstitute.similarity_score.desc())
    )
    result = await db.execute(stmt)
    subs = result.scalars().all()

    items = []
    for s in subs:
        sub_med = s.substitute_medicine
        if not sub_med:
            continue
        first_variant = sub_med.variants[0] if sub_med.variants else None
        mfg_name = first_variant.manufacturer.name if first_variant and first_variant.manufacturer else None
        mrp_val = float(first_variant.mrp) if first_variant and first_variant.mrp is not None else None

        items.append(
            SubstituteItem(
                substitute_id=s.substitute_id,
                substitute_medicine_id=s.substitute_medicine_id,
                brand_name=sub_med.brand_name,
                generic_name=sub_med.generic_name,
                strength=sub_med.strength,
                dosage_form=sub_med.dosage_form,
                manufacturer=mfg_name,
                mrp=mrp_val,
                similarity_score=float(s.similarity_score),
            )
        )
    return items


async def _format_medicine_detail(session: AsyncSession, med: Medicine) -> MedicineDetailRead:
    """Helper to assemble nested MedicineDetailRead response."""
    # Check active alerts
    alert_stmt = (
        select(func.count(RegulatoryAlert.alert_id))
        .where(RegulatoryAlert.medicine_id == med.medicine_id)
        .where(RegulatoryAlert.is_active == True)
    )
    alert_res = await session.execute(alert_stmt)
    alerts_count = alert_res.scalar() or 0

    # Fetch substitutes
    subs_stmt = (
        select(MedicineSubstitute)
        .options(
            selectinload(MedicineSubstitute.substitute_medicine)
            .selectinload(Medicine.variants)
            .selectinload(MedicineVariant.manufacturer)
        )
        .where(MedicineSubstitute.medicine_id == med.medicine_id)
    )
    subs_res = await session.execute(subs_stmt)
    subs = subs_res.scalars().all()

    substitute_items = []
    for s in subs:
        sub_med = s.substitute_medicine
        if not sub_med:
            continue
        v0 = sub_med.variants[0] if sub_med.variants else None
        substitute_items.append(
            SubstituteItem(
                substitute_id=s.substitute_id,
                substitute_medicine_id=s.substitute_medicine_id,
                brand_name=sub_med.brand_name,
                generic_name=sub_med.generic_name,
                strength=sub_med.strength,
                dosage_form=sub_med.dosage_form,
                manufacturer=v0.manufacturer.name if v0 and v0.manufacturer else None,
                mrp=float(v0.mrp) if v0 and v0.mrp is not None else None,
                similarity_score=float(s.similarity_score),
            )
        )

    # Gather images from all variants
    all_images = []
    variant_reads = []
    for v in med.variants:
        for img in v.images:
            all_images.append(img)
        variant_reads.append(
            MedicineVariantRead(
                variant_id=v.variant_id,
                medicine_id=v.medicine_id,
                manufacturer_id=v.manufacturer_id,
                manufacturer_name=v.manufacturer.name if v.manufacturer else None,
                pack_size=v.pack_size,
                unit=v.unit,
                packaging_description=v.packaging_description,
                mrp=float(v.mrp) if v.mrp is not None else None,
                ceiling_price=float(v.ceiling_price) if v.ceiling_price is not None else None,
                batch_number=v.batch_number,
                expiry_date=v.expiry_date,
                source_id=v.source_id,
                created_at=v.created_at,
                updated_at=v.updated_at,
                codes=v.codes,
                images=v.images,
            )
        )

    return MedicineDetailRead(
        medicine_id=med.medicine_id,
        brand_name=med.brand_name,
        generic_name=med.generic_name,
        dosage_form=med.dosage_form,
        strength=med.strength,
        composition=med.composition,
        therapeutic_category=med.therapeutic_category or [],
        prescription_status=med.prescription_status,
        is_discontinued=med.is_discontinued,
        source_id=med.source_id,
        source_name=med.source.source_name if med.source else None,
        source_verification_status=med.source.verification_status if med.source else None,
        confidence_score=float(med.confidence_score) if med.confidence_score is not None else 0.85,
        created_at=med.created_at,
        updated_at=med.updated_at,
        variants=variant_reads,
        images=all_images,
        substitutes=substitute_items,
        has_active_alerts=alerts_count > 0,
        alerts_count=alerts_count,
    )

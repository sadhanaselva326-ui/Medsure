from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.medicine import MedicineMaster
from app.models.variant import MedicineVariant
from app.models.manufacturer import Manufacturer
from app.models.alerts import RegulatoryAlert
from app.models.codes import MedicineIdentifier
from app.api.v1.medicines import router as medicines_router
from app.api.v1.manufacturers import router as manufacturers_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.verification import router as verification_router
from app.api.v1.admin import router as admin_router

v1_router = APIRouter()


@v1_router.get("/stats", tags=["Public Stats"])
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """Public catalogue statistics for transparency and status display."""
    total_meds = (await db.execute(select(func.count(MedicineMaster.medicine_id)))).scalar() or 0
    total_vars = (await db.execute(select(func.count(MedicineVariant.variant_id)))).scalar() or 0
    total_mfgs = (await db.execute(select(func.count(Manufacturer.manufacturer_id)))).scalar() or 0
    total_alerts = (await db.execute(select(func.count(RegulatoryAlert.alert_id)))).scalar() or 0
    total_idents = (await db.execute(select(func.count(MedicineIdentifier.identifier_id)))).scalar() or 0

    verified_official = (await db.execute(
        select(func.count(MedicineMaster.medicine_id)).where(MedicineMaster.verification_status == "verified")
    )).scalar() or 0

    unverified_sample = (await db.execute(
        select(func.count(MedicineMaster.medicine_id)).where(MedicineMaster.verification_status != "verified")
    )).scalar() or 0

    alerts_verified = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(
            RegulatoryAlert.verification_status.in_(["verified", "verified_source"]),
            RegulatoryAlert.source_file_hash.isnot(None),
        )
    )).scalar() or 0

    alerts_unverified = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(
            or_(
                RegulatoryAlert.verification_status.notin_(["verified", "verified_source"]),
                RegulatoryAlert.source_file_hash.is_(None),
            )
        )
    )).scalar() or 0

    # Query notice months
    central_months = [
        r[0] for r in (await db.execute(
            select(RegulatoryAlert.notice_month)
            .where(RegulatoryAlert.is_state == False, RegulatoryAlert.notice_month.isnot(None))
            .distinct()
            .order_by(RegulatoryAlert.notice_month)
        )).all()
    ]

    state_months = [
        r[0] for r in (await db.execute(
            select(RegulatoryAlert.notice_month)
            .where(RegulatoryAlert.is_state == True, RegulatoryAlert.notice_month.isnot(None))
            .distinct()
            .order_by(RegulatoryAlert.notice_month)
        )).all()
    ]

    total_central_alerts = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(RegulatoryAlert.is_state == False)
    )).scalar() or 0

    total_state_alerts = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(RegulatoryAlert.is_state == True)
    )).scalar() or 0

    all_months = sorted(list(set(central_months + state_months)))

    coverage_metadata = {
        "months_imported": all_months,
        "central_notices": central_months,
        "state_notices": state_months,
        "total_central_alerts": total_central_alerts,
        "total_state_alerts": total_state_alerts,
        "note": "Coverage is partial; absence of an alert does not mean a batch is free of problems.",
    }

    rows = (await db.execute(
        select(MedicineMaster.source_name, func.count(MedicineMaster.medicine_id))
        .where(MedicineMaster.source_name.isnot(None))
        .group_by(MedicineMaster.source_name)
    )).all()
    coverage_by_source = {r[0]: r[1] for r in rows}
    coverage_by_source["cdsco_nsq"] = total_alerts

    return {
        "total_medicines": total_meds,
        "total_variants": total_vars,
        "total_manufacturers": total_mfgs,
        "total_identifiers": total_idents,
        "total_alerts": total_alerts,
        "verified_official": verified_official,
        "unverified_sample": unverified_sample,
        "alerts_verified": alerts_verified,
        "alerts_unverified": alerts_unverified,
        "coverage": coverage_metadata,
        "coverage_by_source": coverage_by_source,
        "notice": "The medicine catalogue contains 119 unverified baseline sample records. CDSCO NSQ alert rows are imported from official PDF notices and marked verified_source.",
    }


v1_router.include_router(medicines_router)
v1_router.include_router(manufacturers_router)
v1_router.include_router(alerts_router)
v1_router.include_router(verification_router)
v1_router.include_router(admin_router)

__all__ = ["v1_router"]

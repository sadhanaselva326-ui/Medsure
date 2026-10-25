from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models.sources import DataSource
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.manufacturer import Manufacturer
from app.models.codes import MedicineCode
from app.models.alerts import RegulatoryAlert
from app.schemas.sources import DataSourceCreate, DataSourceRead
from app.schemas.ingestion import IngestRequest, IngestStats, AdminStatsResponse
from app.services.ingestion_service import ingest_dataset

router = APIRouter(prefix="/admin", tags=["Admin & Data Ingestion"])


@router.post("/sources", response_model=DataSourceRead, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    payload: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_admin_key),
):
    """Register a new authoritative data source (ABDM, NPPA, GS1, Kaggle, etc.)."""
    # Check if exists
    stmt = select(DataSource).where(DataSource.source_name == payload.source_name)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source '{payload.source_name}' already exists.",
        )

    source = DataSource(
        source_name=payload.source_name,
        source_type=payload.source_type,
        source_url=payload.source_url,
        api_endpoint=payload.api_endpoint,
        verification_status=payload.verification_status,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/sources", response_model=List[DataSourceRead])
async def list_data_sources(
    db: AsyncSession = Depends(get_db),
):
    """List all registered data sources with current coverage counts and sync timestamps."""
    stmt = select(DataSource)
    res = await db.execute(stmt)
    sources = list(res.scalars().all())
    # Ensure coverage_count accurately reflects actual imported database records
    for s in sources:
        med_cnt = (
            await db.execute(
                select(func.count(Medicine.medicine_id)).where(
                    Medicine.source_name == s.source_name,
                    Medicine.is_demo == False,
                )
            )
        ).scalar() or 0
        if med_cnt == 0:
            alert_cnt = (
                await db.execute(
                    select(func.count(RegulatoryAlert.alert_id)).where(
                        RegulatoryAlert.source_name == s.source_name
                    )
                )
            ).scalar() or 0
            s.coverage_count = alert_cnt
        else:
            s.coverage_count = med_cnt
    sources.sort(key=lambda x: x.coverage_count, reverse=True)
    return sources


@router.post("/ingest", response_model=IngestStats)
async def ingest_medicines(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_admin_key),
):
    """Bulk ingest medicines, variants, and codes from CSV or JSON dataset."""
    try:
        return await ingest_dataset(session=db, payload=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}")


@router.get("/stats", response_model=AdminStatsResponse)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_admin_key),
):
    """Get overall database metrics: medicine counts, variants, manufacturers, and coverage by source."""
    from app.models.import_run import DataImportRun
    from app.schemas.ingestion import DataImportRunItem

    med_count = (await db.execute(select(func.count(Medicine.medicine_id)))).scalar() or 0
    demo_count = (await db.execute(select(func.count(Medicine.medicine_id)).where(Medicine.is_demo == True))).scalar() or 0
    official_count = (await db.execute(select(func.count(Medicine.medicine_id)).where(Medicine.is_demo == False))).scalar() or 0
    var_count = (await db.execute(select(func.count(MedicineVariant.variant_id)))).scalar() or 0
    mfg_count = (await db.execute(select(func.count(Manufacturer.manufacturer_id)))).scalar() or 0
    code_count = (await db.execute(select(func.count(MedicineCode.identifier_id)))).scalar() or 0
    alert_count = (await db.execute(select(func.count(RegulatoryAlert.alert_id)))).scalar() or 0

    verified_official = (await db.execute(
        select(func.count(Medicine.medicine_id)).where(Medicine.verification_status == "verified")
    )).scalar() or 0

    unverified_sample = (await db.execute(
        select(func.count(Medicine.medicine_id)).where(Medicine.verification_status != "verified")
    )).scalar() or 0

    alerts_verified = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(RegulatoryAlert.verification_status == "verified")
    )).scalar() or 0

    alerts_unverified = (await db.execute(
        select(func.count(RegulatoryAlert.alert_id)).where(RegulatoryAlert.verification_status != "verified")
    )).scalar() or 0

    # Derive coverage from actual imported records, NOT from stale data_source.coverage_count
    med_by_source_stmt = (
        select(Medicine.source_name, func.count(Medicine.medicine_id))
        .where(Medicine.source_name.isnot(None))
        .group_by(Medicine.source_name)
    )
    med_by_source = (await db.execute(med_by_source_stmt)).all()
    coverage = {row[0]: row[1] for row in med_by_source}

    # Add CDSCO NSQ alert count (alerts, not medicines)
    cdsco_alert_count = (
        await db.execute(
            select(func.count(RegulatoryAlert.alert_id)).where(
                RegulatoryAlert.source_name == "cdsco_nsq"
            )
        )
    ).scalar() or 0
    if cdsco_alert_count > 0:
        coverage["cdsco_nsq (alerts)"] = cdsco_alert_count

    # Fetch recent import runs
    runs_stmt = select(DataImportRun).order_by(DataImportRun.started_at.desc()).limit(10)
    runs = (await db.execute(runs_stmt)).scalars().all()
    runs_items = [
        DataImportRunItem(
            run_id=r.run_id,
            source_name=r.source_name,
            adapter_name=r.adapter_name,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            records_read=r.records_read,
            records_imported=r.records_imported,
            records_updated=r.records_updated,
            records_skipped=r.records_skipped,
            errors_count=r.errors_count,
            error_summary=r.error_summary,
        )
        for r in runs
    ]

    last_run = runs_items[0] if runs_items else None

    return AdminStatsResponse(
        total_medicines=med_count,
        total_variants=var_count,
        total_manufacturers=mfg_count,
        total_codes=code_count,
        total_identifiers=code_count,
        total_alerts=alert_count,
        demo_records_count=demo_count,
        official_records_count=verified_official,
        verified_official=verified_official,
        unverified_sample=unverified_sample,
        alerts_verified=alerts_verified,
        alerts_unverified=alerts_unverified,
        notice="The catalogue currently contains unverified sample data. Official document import is in progress.",
        coverage_by_source=coverage,
        last_import_run=last_run,
        recent_import_runs=runs_items,
    )

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.verification import (
    ScanAnalyzeRequest,
    ScanAnalyzeResponse,
    MedicineVerifyRequest,
    MedicineVerifyResponse,
)
from app.services.verification_service import (
    analyze_scan_or_query,
    verify_medicine_strict,
)

router = APIRouter(tags=["Verification & OCR Analysis"])


@router.post("/scan/analyze", response_model=ScanAnalyzeResponse)
async def scan_analyze_endpoint(
    payload: ScanAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Analyze scanned packaging, barcode, or OCR text against Indian medicine master database

    with comprehensive risk assessment and recall checking.
    """
    return await analyze_scan_or_query(session=db, payload=payload)


@router.post("/medicine/verify", response_model=MedicineVerifyResponse)
async def medicine_verify_endpoint(
    payload: MedicineVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Strict verification returning VERIFIED, NEEDS_VERIFICATION, HIGH_RISK, or NO_MATCH

    with full risk explanation and confidence score.
    """
    return await verify_medicine_strict(session=db, payload=payload)

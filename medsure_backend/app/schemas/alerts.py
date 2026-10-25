from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RegulatoryAlertBase(BaseModel):
    alert_type: str = Field(
        ...,
        description="Type: recall, advisory, quality_alert, batch_alert, price_violation, nsq_alert, spurious",
    )
    batch_number: Optional[str] = None
    manufacturer: Optional[str] = None
    # notice month string from the official PDF, e.g. "April 2025" – stored as plain text, never parsed as date
    alert_date: str = Field(..., description="Notice month from PDF (e.g. 'April 2025')")
    source_url: Optional[str] = None
    description: str
    is_active: bool = True
    medicine_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    source_id: Optional[UUID] = None


class RegulatoryAlertCreate(RegulatoryAlertBase):
    pass


class RegulatoryAlertRead(RegulatoryAlertBase):
    model_config = ConfigDict(from_attributes=True)

    alert_id: UUID
    created_at: datetime
    imported_at: Optional[datetime] = None       # timestamp when row was ingested
    internal_ref: Optional[str] = None           # MedSure reference (MEDSURE-REF-…), not an official notice number
    risk_rating: Optional[str] = None            # derived by MedSure; describes quality failure type
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    drug_name: Optional[str] = None
    reason_for_nsq: Optional[str] = None
    testing_lab: Optional[str] = None
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    notice_month: Optional[str] = None
    source_file_name: Optional[str] = None
    source_file_hash: Optional[str] = None
    page_number: Optional[int] = None
    s_no_in_pdf: Optional[int] = None            # serial number printed in the PDF table
    row_index_on_page: Optional[int] = None      # 1-indexed row position on that PDF page
    row_number: Optional[int] = None             # backwards-compatible alias for s_no_in_pdf
    is_state: Optional[bool] = None
    licence_note: Optional[str] = None
    source_record_id: Optional[str] = None

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source_id: UUID = Field(..., description="Target data source UUID")
    file_url: Optional[str] = Field(None, description="URL or local path to CSV or JSON data")
    format: str = Field("csv", description="Format of the data: csv, json")
    batch_size: int = Field(500, ge=1, le=5000)
    raw_data: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional inline data array for direct ingestion without external URL",
    )


class IngestStats(BaseModel):
    source_id: UUID
    source_name: str
    total_processed: int = 0
    imported: int = 0
    updated_reused: int = 0
    skipped: int = 0
    failed: int = 0
    duplicate_records: int = 0
    manufacturers_created: int = 0
    variants_created: int = 0
    errors: List[str] = []


class DataImportRunItem(BaseModel):
    run_id: UUID
    source_name: str
    adapter_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_read: int = 0
    records_imported: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors_count: int = 0
    error_summary: Optional[str] = None


class AdminStatsResponse(BaseModel):
    total_medicines: int
    total_variants: int
    total_manufacturers: int
    total_codes: int
    total_identifiers: int = 0
    total_alerts: int
    demo_records_count: int = 0
    official_records_count: int = 0
    verified_official: int = 0
    unverified_sample: int = 0
    alerts_verified: int = 0
    alerts_unverified: int = 0
    notice: str = "The catalogue currently contains unverified sample data. Official document import is in progress."
    coverage_by_source: Dict[str, int]
    last_import_run: Optional[DataImportRunItem] = None
    recent_import_runs: List[DataImportRunItem] = []

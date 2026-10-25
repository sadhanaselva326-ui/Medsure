from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    source_name: str = Field(..., description="Unique source name, e.g. abdm_cdci, nppa_ipdms")
    source_type: str = Field(
        ...,
        description="Type: government, manufacturer, third_party, user_submitted, aggregator",
    )
    source_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    verification_status: str = Field("pending", description="verified, pending, or unverified")


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceRead(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)

    source_id: UUID
    coverage_count: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime

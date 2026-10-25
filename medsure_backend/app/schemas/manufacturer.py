from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ManufacturerBase(BaseModel):
    name: str
    address: Optional[str] = None
    gstin: Optional[str] = None
    verification_status: str = Field("pending", description="verified, pending, unverified")
    source_id: Optional[UUID] = None


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerRead(ManufacturerBase):
    model_config = ConfigDict(from_attributes=True)

    manufacturer_id: UUID
    created_at: datetime
    updated_at: datetime


class ManufacturerMedicineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_id: UUID
    brand_name: str
    generic_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = None


class ManufacturerDetailRead(ManufacturerRead):
    medicines: List[ManufacturerMedicineItem] = []

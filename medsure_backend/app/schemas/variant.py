from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MedicineCodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code_id: UUID
    variant_id: UUID
    gtin: Optional[str] = None
    barcode: Optional[str] = None
    qr_identifier: Optional[str] = None
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    source: Optional[str] = "GS1"
    verified: bool = False
    verified_at: Optional[datetime] = None
    created_at: datetime


class MedicineCodeCreate(BaseModel):
    gtin: Optional[str] = None
    barcode: Optional[str] = None
    qr_identifier: Optional[str] = None
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    source: Optional[str] = "GS1"
    verified: bool = False


class MedicineImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_id: UUID
    variant_id: UUID
    image_url: str
    image_type: str
    source: Optional[str] = "manufacturer"
    verified: bool = False
    created_at: datetime


class MedicineImageCreate(BaseModel):
    image_url: str
    image_type: str = "pack_front"
    source: Optional[str] = "manufacturer"
    verified: bool = False


class MedicineVariantBase(BaseModel):
    pack_size: Optional[int] = None
    unit: Optional[str] = None
    packaging_description: Optional[str] = None
    mrp: Optional[float] = None
    ceiling_price: Optional[float] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacturer_id: Optional[UUID] = None
    source_id: Optional[UUID] = None


class MedicineVariantCreate(MedicineVariantBase):
    medicine_id: UUID
    codes: Optional[List[MedicineCodeCreate]] = []
    images: Optional[List[MedicineImageCreate]] = []


class MedicineVariantRead(MedicineVariantBase):
    model_config = ConfigDict(from_attributes=True)

    variant_id: UUID
    medicine_id: UUID
    manufacturer_name: Optional[str] = None
    codes: List[MedicineCodeRead] = []
    images: List[MedicineImageRead] = []
    created_at: datetime
    updated_at: datetime

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.variant import MedicineVariantRead, MedicineImageRead


class ActiveIngredient(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class MedicineComposition(BaseModel):
    active_ingredients: List[ActiveIngredient] = []
    excipients: List[str] = []


class MedicineBase(BaseModel):
    brand_name: str
    generic_name: str
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    composition: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"active_ingredients": [], "excipients": []}
    )
    therapeutic_category: Optional[List[str]] = Field(default_factory=list)
    prescription_status: str = Field("prescription", description="prescription, otc, restricted")
    is_discontinued: bool = False
    source_id: Optional[UUID] = None
    source_name: Optional[str] = None
    is_demo: bool = False
    last_verified_at: Optional[datetime] = None
    confidence_score: float = Field(0.85, ge=0.0, le=1.0)


class MedicineCreate(MedicineBase):
    pass


class MedicineRead(MedicineBase):
    model_config = ConfigDict(from_attributes=True)

    medicine_id: UUID
    source_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MedicineSearchResultItem(BaseModel):
    medicine_id: UUID
    brand_name: str
    generic_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    manufacturer: Optional[str] = None
    mrp: Optional[float] = None
    pack_size: Optional[int] = None
    unit: Optional[str] = None
    source: Optional[str] = None
    source_name: Optional[str] = None
    is_demo: bool = False
    confidence_score: float = 0.85
    relevance_score: float = 1.0


class SubstituteItem(BaseModel):
    substitute_id: UUID
    substitute_medicine_id: UUID
    brand_name: str
    generic_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    manufacturer: Optional[str] = None
    mrp: Optional[float] = None
    similarity_score: float


class MedicineDetailRead(MedicineRead):
    source_name: Optional[str] = None
    source_verification_status: Optional[str] = None
    variants: List[MedicineVariantRead] = []
    images: List[MedicineImageRead] = []
    substitutes: List[SubstituteItem] = []
    has_active_alerts: bool = False
    alerts_count: int = 0

from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.alerts import RegulatoryAlertRead


class ExtractedFields(BaseModel):
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    ingredients: Optional[str] = None
    composition: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    pack_size: Optional[Any] = None
    mrp: Optional[float] = None


class ScanAnalyzeRequest(BaseModel):
    ocr_text: Optional[str] = Field(
        None,
        description="Raw OCR text extracted from package or strip",
        examples=["Paracetamol Tablets IP 500mg Batch: B-1024 Exp: 12/2027"],
    )
    barcode: Optional[str] = Field(None, description="13-digit EAN barcode (starts with 890 for India)")
    gtin: Optional[str] = Field(None, description="14-digit Global Trade Item Number")
    name: Optional[str] = Field(None, description="Medicine brand or formulation name")
    brand_name: Optional[str] = Field(None, description="Medicine brand name")
    generic_name: Optional[str] = Field(None, description="Generic formulation name")
    ingredients: Optional[str] = Field(None, description="Active ingredients")
    composition: Optional[str] = Field(None, description="Composition formulation")
    strength: Optional[str] = Field(None, description="Dosage strength (e.g. 500 mg)")
    dosage_form: Optional[str] = Field(None, description="Dosage form (e.g. Tablet, Capsule)")
    manufacturer: Optional[str] = Field(None, description="Declared manufacturer")
    batch_number: Optional[str] = Field(None, description="Batch number to check against regulatory alerts")
    expiry_date: Optional[str] = Field(None, description="Expiry date on package")
    pack_size: Optional[Any] = Field(None, description="Pack size")
    mrp: Optional[float] = Field(None, description="Maximum Retail Price (INR)")
    extracted_fields: Optional[ExtractedFields] = Field(default_factory=ExtractedFields)


class MatchedMedicineItem(BaseModel):
    medicine_id: UUID
    brand_name: str
    generic_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence_score: Optional[float] = None
    match_flags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    source_record_id: Optional[str] = None
    source_url: Optional[str] = None
    verification_status: Optional[str] = "unverified_source"
    mrp: Optional[float] = None
    ceiling_price: Optional[float] = None
    pack_size: Optional[Any] = None
    unit: Optional[str] = None


class Layer1Result(BaseModel):
    layer: str = "Layer 1: Identifier"
    checked: bool = False
    status: str = "SKIPPED"  # MATCH, NO_MATCH, SKIPPED, INVALID
    identifier_type: Optional[str] = None
    identifier_value: Optional[str] = None
    details: Optional[str] = None


class FieldMatchResult(BaseModel):
    field: str
    input_value: Optional[str] = None
    catalog_value: Optional[str] = None
    status: str  # match, mismatch, missing


class Layer2Result(BaseModel):
    layer: str = "Layer 2: Details & Pricing"
    checked: bool = False
    status: str = "SKIPPED"  # MATCH, PARTIAL_MATCH, MISMATCH, NO_MATCH, SKIPPED
    score: Optional[float] = None
    field_results: Dict[str, FieldMatchResult] = Field(default_factory=dict)
    mismatched_fields: List[str] = Field(default_factory=list)
    price_check: Optional[Dict[str, Any]] = None
    details: Optional[str] = None


class Layer3Result(BaseModel):
    layer: str = "Layer 3: Batch Regulatory Alerts"
    checked: bool = False
    status: str = "SKIPPED"  # ALERT_FOUND, CLEAR, SKIPPED
    batch_number: Optional[str] = None
    alerts_count: int = 0
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    details: Optional[str] = None


class PerLayerResults(BaseModel):
    layer_1_identifier: Layer1Result
    layer_2_details: Layer2Result
    layer_3_batch_alerts: Layer3Result


class RiskAssessment(BaseModel):
    overall_risk: str = Field(..., description="low, medium, high")
    flags: List[str] = Field(default_factory=list)
    recommendation: str = Field(
        ...,
        description="Allowed status label or legacy recommendation code",
    )
    explanation: str


class ScanAnalyzeResponse(BaseModel):
    status: str = Field(
        ...,
        description="Must be one of the 5 allowed labels: Matches a catalogue record, Needs verification, Regulatory alert found, No matching record in the MedSure catalogue, Insufficient input",
    )
    confidence: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    matched_record: Optional[MatchedMedicineItem] = None
    matched_medicines: List[MatchedMedicineItem] = Field(default_factory=list)
    per_layer_results: Optional[PerLayerResults] = None
    mismatched_fields: List[str] = Field(default_factory=list)
    regulatory_alerts: List[RegulatoryAlertRead] = Field(default_factory=list)
    evidence_links: List[Dict[str, str]] = Field(default_factory=list)
    disclaimer: str = (
        "MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. Consult a pharmacist."
    )
    risk_assessment: Optional[RiskAssessment] = None
    recommendation: Optional[str] = None


class MedicineVerifyRequest(ScanAnalyzeRequest):
    strict_mode: bool = Field(True, description="Enforce strict matching on strength and manufacturer")


class MedicineVerifyResponse(BaseModel):
    status: str = Field(..., description="Mapped to allowed label")
    confidence: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    medicine: Optional[MatchedMedicineItem] = None
    matched_medicines: List[MatchedMedicineItem] = Field(default_factory=list)
    per_layer_results: Optional[PerLayerResults] = None
    mismatched_fields: List[str] = Field(default_factory=list)
    regulatory_alerts: List[RegulatoryAlertRead] = Field(default_factory=list)
    evidence_links: List[Dict[str, str]] = Field(default_factory=list)
    disclaimer: str = (
        "MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. Consult a pharmacist."
    )
    risk_assessment: Optional[RiskAssessment] = None

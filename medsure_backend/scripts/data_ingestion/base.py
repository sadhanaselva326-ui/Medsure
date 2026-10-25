"""base.py - Base classes, interfaces, and data models for MedSure ingestion adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional


@dataclass
class ProvenanceMeta:
    """Metadata tracking the authoritative provenance of an imported record."""
    source_name: str
    source_url: str
    retrieval_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_record_id: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    is_demo: bool = False


@dataclass
class RawMedicineRecord:
    """Standardized intermediate record emitted by source adapters."""
    # Formulation (MedicineMaster)
    brand_name: str
    generic_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = "Tablet"
    composition: Dict[str, Any] = field(default_factory=lambda: {"active_ingredients": [], "excipients": []})
    therapeutic_category: List[str] = field(default_factory=list)
    prescription_status: str = "prescription"
    confidence_score: float = 0.95

    # Packaging Variant (MedicineVariant)
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None
    pack_size: Optional[int] = 10
    unit: Optional[str] = "tablet"
    packaging_description: Optional[str] = None
    mrp: Optional[float] = None
    ceiling_price: Optional[float] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None

    # Identifiers (MedicineIdentifier)
    gtin: Optional[str] = None
    barcode: Optional[str] = None
    identifier_type: Optional[str] = None
    identifier_value: Optional[str] = None

    # Provenance
    provenance: Optional[ProvenanceMeta] = None


@dataclass
class RawRegulatoryAlert:
    """Standardized regulatory alert / recall / NSQ notice emitted by alert adapters."""
    medicine_brand: Optional[str] = None
    generic_name: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturer_name: Optional[str] = None
    alert_date: date = field(default_factory=date.today)
    alert_type: str = "nsq_alert"  # 'recall', 'nsq_alert', 'quality_alert', 'price_violation'
    severity: str = "high"
    description: str = ""
    reason_for_nsq: Optional[str] = None
    testing_lab: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    retrieval_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_demo: bool = False
    is_fixture: bool = False


@dataclass
class ImportStats:
    """Tracks counts and errors for an ingestion execution."""
    source_name: str
    adapter_name: str
    records_read: int = 0
    records_imported: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors_count: int = 0
    error_summary: List[str] = field(default_factory=list)
    status: str = "completed"


class BaseSourceImporter(ABC):
    """Abstract Base Class for official Indian medicine data source adapters."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Machine identifier for data source e.g. 'pmbi_janaushadhi'."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Category: 'government', 'manufacturer', 'third_party', 'aggregator'."""
        pass

    @property
    @abstractmethod
    def source_url(self) -> str:
        """Official website or portal URL."""
        pass

    @abstractmethod
    async def load_records(self) -> List[RawMedicineRecord]:
        """Loads and normalizes medicine records from official source."""
        pass

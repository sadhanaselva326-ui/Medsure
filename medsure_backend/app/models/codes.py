import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property

from app.database import Base, GUID


class MedicineIdentifier(Base):
    __tablename__ = "medicine_identifier"

    identifier_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    variant_id = Column(
        GUID,
        ForeignKey("medicine_variant.variant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identifier_type = Column(String(30), default="barcode", nullable=False, index=True)
    identifier_value = Column(String(100), nullable=False, index=True)
    gtin = Column(String(14), unique=True, nullable=True, index=True)
    barcode = Column(String(30), nullable=True, index=True)
    qr_identifier = Column(Text, nullable=True)
    batch_number = Column(Text, nullable=True)
    serial_number = Column(Text, nullable=True)

    # Source provenance
    source_name = Column(String(50), default="GS1", nullable=True)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(Text, nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    def __init__(self, **kwargs):
        if "source" in kwargs and "source_name" not in kwargs:
            kwargs["source_name"] = kwargs.pop("source")
        if "code_id" in kwargs and "identifier_id" not in kwargs:
            kwargs["identifier_id"] = kwargs.pop("code_id")
        if "identifier_value" not in kwargs:
            kwargs["identifier_value"] = kwargs.get("gtin") or kwargs.get("barcode") or ""
        if "identifier_type" not in kwargs:
            if kwargs.get("gtin"):
                kwargs["identifier_type"] = "gtin"
            elif kwargs.get("barcode"):
                kwargs["identifier_type"] = "barcode"
            else:
                kwargs["identifier_type"] = "barcode"
        super().__init__(**kwargs)

    @hybrid_property
    def code_id(self):
        """Backward compatibility for existing code referring to code_id."""
        return self.identifier_id

    @hybrid_property
    def source(self):
        """Backward compatibility for existing code referring to source."""
        return self.source_name

    @source.setter
    def source(self, value):
        self.source_name = value

    # Relationships
    variant = relationship("MedicineVariant", back_populates="identifiers")

    __table_args__ = (
        Index("idx_identifier_type_val", "identifier_type", "identifier_value"),
        Index("idx_codes_gtin", "gtin"),
        Index("idx_codes_barcode", "barcode"),
        Index("idx_codes_variant_id", "variant_id"),
        Index("idx_identifier_is_demo", "is_demo"),
    )


# Alias for backward compatibility
MedicineCode = MedicineIdentifier

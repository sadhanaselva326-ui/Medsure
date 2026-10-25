import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class MedicineVariant(Base):
    __tablename__ = "medicine_variant"

    variant_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    medicine_id = Column(
        GUID,
        ForeignKey("medicine_master.medicine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manufacturer_id = Column(
        GUID,
        ForeignKey("manufacturer.manufacturer_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pack_size = Column(Integer, nullable=True)
    unit = Column(Text, nullable=True)  # 'tablet', 'capsule', 'ml', 'strip', 'bottle', 'vial'
    packaging_description = Column(Text, nullable=True)
    mrp = Column(Numeric(10, 2), nullable=True, index=True)
    ceiling_price = Column(Numeric(10, 2), nullable=True)
    batch_number = Column(Text, nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Source provenance and audit fields
    source_id = Column(
        GUID,
        ForeignKey("data_source.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    source_name = Column(Text, nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(Text, nullable=True, index=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    variant_hash = Column(String(64), nullable=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    medicine = relationship("MedicineMaster", back_populates="variants")
    manufacturer = relationship("Manufacturer", back_populates="variants")
    source = relationship("DataSource", back_populates="variants")
    identifiers = relationship("MedicineIdentifier", back_populates="variant", cascade="all, delete-orphan")
    codes = relationship("MedicineIdentifier", back_populates="variant", overlaps="identifiers")  # Alias for existing code
    prices = relationship("MedicinePrice", back_populates="variant", cascade="all, delete-orphan")
    images = relationship("MedicineImage", back_populates="variant", cascade="all, delete-orphan")
    regulatory_alerts = relationship("RegulatoryAlert", back_populates="variant")

    __table_args__ = (
        Index("idx_variants_medicine_id", "medicine_id"),
        Index("idx_variants_manufacturer_id", "manufacturer_id"),
        Index("idx_variants_mrp", "mrp"),
        Index("idx_variant_hash", "variant_hash"),
        Index("idx_variant_is_demo", "is_demo"),
    )

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    CheckConstraint,
    JSON,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class MedicineMaster(Base):
    __tablename__ = "medicine_master"

    medicine_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    generic_name = Column(Text, nullable=False, index=True)
    brand_name = Column(Text, nullable=False, index=True)
    dosage_form = Column(Text, nullable=True)
    strength = Column(Text, nullable=True)
    composition = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=lambda: {"active_ingredients": [], "excipients": []},
    )
    therapeutic_category = Column(
        ARRAY(Text).with_variant(JSON, "sqlite"),
        nullable=True,
        default=list,
    )
    prescription_status = Column(
        String(20),
        CheckConstraint(
            "prescription_status IN ('prescription', 'otc', 'restricted', 'unknown')",
            name="check_medicine_prescription_status",
        ),
        default="prescription",
        nullable=False,
    )
    is_discontinued = Column(Boolean, default=False, nullable=False)
    source_id = Column(GUID, ForeignKey("data_source.source_id", ondelete="SET NULL"), nullable=True)
    confidence_score = Column(
        Numeric(5, 4),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="check_medicine_confidence_score",
        ),
        default=0.85,
        nullable=False,
    )

    # Source provenance and audit fields
    source_name = Column(Text, nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(Text, nullable=True, index=True)
    source_file_name = Column(Text, nullable=True)
    source_file_hash = Column(String(64), nullable=True)
    licence_note = Column(Text, nullable=True)
    verification_status = Column(String(30), default="unverified_source", nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    normalization_hash = Column(String(64), nullable=True, index=True)

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
    source = relationship("DataSource", back_populates="medicines")
    variants = relationship("MedicineVariant", back_populates="medicine", cascade="all, delete-orphan")
    regulatory_alerts = relationship("RegulatoryAlert", back_populates="medicine")
    substitutes = relationship(
        "MedicineSubstitute",
        foreign_keys="[MedicineSubstitute.medicine_id]",
        back_populates="medicine",
        cascade="all, delete-orphan",
    )
    substituted_by = relationship(
        "MedicineSubstitute",
        foreign_keys="[MedicineSubstitute.substitute_medicine_id]",
        back_populates="substitute_medicine",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "idx_medicines_brand_name_fts",
            text("to_tsvector('english', brand_name)"),
            postgresql_using="gin",
        ),
        Index(
            "idx_medicines_generic_name_fts",
            text("to_tsvector('english', generic_name)"),
            postgresql_using="gin",
        ),
        Index(
            "idx_medicines_brand_name_trgm",
            "brand_name",
            postgresql_using="gin",
            postgresql_ops={"brand_name": "gin_trgm_ops"},
        ),
        Index(
            "idx_medicines_generic_name_trgm",
            "generic_name",
            postgresql_using="gin",
            postgresql_ops={"generic_name": "gin_trgm_ops"},
        ),
        Index("idx_medicine_norm_hash", "normalization_hash"),
        Index("idx_medicine_is_demo", "is_demo"),
        Index("idx_medicine_source_record", "source_name", "source_record_id"),
    )


# Alias for backward compatibility
Medicine = MedicineMaster

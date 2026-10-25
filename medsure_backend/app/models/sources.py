import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class DataSource(Base):
    __tablename__ = "data_source"

    source_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    source_name = Column(Text, nullable=False, unique=True, index=True)
    source_type = Column(
        String(30),
        CheckConstraint(
            "source_type IN ('government', 'manufacturer', 'third_party', 'user_submitted', 'aggregator')",
            name="check_source_type",
        ),
        nullable=False,
    )
    source_url = Column(Text, nullable=True)
    api_endpoint = Column(Text, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(
        String(20),
        CheckConstraint(
            "verification_status IN ('verified', 'pending', 'unverified')",
            name="check_source_verification_status",
        ),
        default="pending",
        nullable=False,
    )
    coverage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    manufacturers = relationship("Manufacturer", back_populates="source", cascade="all, delete-orphan")
    medicines = relationship("MedicineMaster", back_populates="source")
    variants = relationship("MedicineVariant", back_populates="source")
    regulatory_alerts = relationship("RegulatoryAlert", back_populates="source")

    __table_args__ = (
        Index("idx_sources_name", "source_name"),
        Index("idx_sources_type", "source_type"),
    )


class SourceDocument(Base):
    __tablename__ = "source_document"

    document_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    source_name = Column(Text, nullable=False, index=True)
    file_name = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    original_document_present = Column(Integer, default=0, nullable=False)
    official_url = Column(Text, nullable=True)
    licence_terms_note = Column(Text, nullable=True)
    produced_by = Column(Text, nullable=False)
    record_count = Column(Integer, default=0, nullable=False)
    verification_status = Column(String(30), nullable=False, default="unverified_source")
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

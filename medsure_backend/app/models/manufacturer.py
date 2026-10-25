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
    CheckConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class Manufacturer(Base):
    __tablename__ = "manufacturer"

    manufacturer_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, index=True)
    raw_name = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(15), nullable=True)
    license_number = Column(String(100), nullable=True)
    verification_status = Column(
        String(20),
        CheckConstraint(
            "verification_status IN ('verified', 'pending', 'unverified')",
            name="check_manufacturer_verification_status",
        ),
        default="pending",
        nullable=False,
    )
    source_id = Column(GUID, ForeignKey("data_source.source_id", ondelete="SET NULL"), nullable=True)
    source_name = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(Text, nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)

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
    source = relationship("DataSource", back_populates="manufacturers")
    variants = relationship("MedicineVariant", back_populates="manufacturer")

    __table_args__ = (
        Index(
            "idx_manufacturers_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "idx_manufacturers_name_fts",
            text("to_tsvector('english', name)"),
            postgresql_using="gin",
        ),
        Index("idx_manufacturer_is_demo", "is_demo"),
    )

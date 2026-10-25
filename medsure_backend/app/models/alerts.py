import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class RegulatoryAlert(Base):
    __tablename__ = "regulatory_alert"

    alert_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    drug_name = Column(Text, nullable=True, index=True)
    medicine_id = Column(
        GUID,
        ForeignKey("medicine_master.medicine_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_id = Column(
        GUID,
        ForeignKey("medicine_variant.variant_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type = Column(
        String(30),
        CheckConstraint(
            "alert_type IN ('recall', 'advisory', 'quality_alert', 'batch_alert', 'price_violation', 'nsq_alert', 'spurious')",
            name="check_alert_type",
        ),
        nullable=False,
    )
    batch_number = Column(Text, nullable=True, index=True)
    manufacturer = Column(Text, nullable=True)
    alert_date = Column(Text, nullable=False, index=True)  # Notice month from official PDF (e.g. "April 2025")
    imported_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    source_url = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    reason_for_nsq = Column(Text, nullable=True)  # Specific CDSCO test failure reason
    testing_lab = Column(Text, nullable=True)     # e.g. Central Drugs Laboratory, Kolkata
    mfg_date = Column(Text, nullable=True)
    exp_date = Column(Text, nullable=True)
    is_state = Column(Boolean, default=False, nullable=False, index=True)
    notice_month = Column(Text, nullable=True, index=True)
    page_number = Column(Integer, nullable=True)
    s_no_in_pdf = Column(Integer, nullable=True)      # Serial number printed in PDF table
    row_index_on_page = Column(Integer, nullable=True)# 1-indexed row position on page
    row_number = Column(Integer, nullable=True)       # Backwards-compatible alias for s_no_in_pdf
    severity = Column(String(50), default="nsq_alert", nullable=True)
    risk_rating = Column(Text, nullable=True)         # Labelled as 'derived by MedSure'
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Source provenance
    source_id = Column(
        GUID,
        ForeignKey("data_source.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    source_name = Column(Text, nullable=True, index=True)
    source_record_id = Column(Text, nullable=True, index=True)
    source_file_name = Column(Text, nullable=True)
    source_file_hash = Column(String(64), nullable=True)
    licence_note = Column(Text, nullable=True)
    verification_status = Column(String(30), default="unverified_source", nullable=True)
    official_notice_ref = Column(Text, nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    is_fixture = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    medicine = relationship("MedicineMaster", back_populates="regulatory_alerts")
    variant = relationship("MedicineVariant", back_populates="regulatory_alerts")
    source = relationship("DataSource", back_populates="regulatory_alerts")

    __table_args__ = (
        Index("idx_alerts_medicine_id", "medicine_id"),
        Index("idx_alerts_batch_num", "batch_number"),
        Index("idx_alerts_alert_date", "alert_date"),
        Index("idx_alerts_severity", "severity"),
        Index("idx_alerts_is_active", "is_active"),
        Index("idx_alerts_is_demo", "is_demo"),
    )

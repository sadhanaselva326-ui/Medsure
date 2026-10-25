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
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class MedicinePrice(Base):
    __tablename__ = "medicine_price"

    price_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    variant_id = Column(
        GUID,
        ForeignKey("medicine_variant.variant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_type = Column(
        String(30),
        default="mrp",
        nullable=False,
        index=True,
    )  # 'mrp', 'ceiling_price', 'pmbi_mrp', 'retail_price'
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    unit = Column(Text, nullable=True)  # '1 Tablet', '1 Strip of 10 Tablets'
    pack_size = Column(Integer, nullable=True)
    effective_date = Column(Date, nullable=True)
    notification_number = Column(Text, nullable=True)  # Official Gazette notification e.g. S.O. 1499(E)

    # Source provenance
    source_name = Column(Text, nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    source_record_id = Column(Text, nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    variant = relationship("MedicineVariant", back_populates="prices")

    __table_args__ = (
        Index("idx_price_variant_type", "variant_id", "price_type"),
        Index("idx_price_source", "source_name"),
        Index("idx_price_is_demo", "is_demo"),
    )

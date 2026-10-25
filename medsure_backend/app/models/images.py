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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class MedicineImage(Base):
    __tablename__ = "medicine_image"

    image_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    variant_id = Column(
        GUID,
        ForeignKey("medicine_variant.variant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = Column(Text, nullable=False)
    image_type = Column(
        String(20),
        CheckConstraint(
            "image_type IN ('pack_front', 'pack_back', 'strip', 'tablet', 'bottle')",
            name="check_image_type",
        ),
        default="pack_front",
        nullable=False,
    )
    source = Column(String(50), default="manufacturer", nullable=True)  # 'manufacturer', 'user_upload', 'scraped'
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    variant = relationship("MedicineVariant", back_populates="images")

    __table_args__ = (
        Index("idx_images_variant_id", "variant_id"),
    )

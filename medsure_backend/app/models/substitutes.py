import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class MedicineSubstitute(Base):
    __tablename__ = "medicine_substitute"

    substitute_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    medicine_id = Column(
        GUID,
        ForeignKey("medicine_master.medicine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    substitute_medicine_id = Column(
        GUID,
        ForeignKey("medicine_master.medicine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity_score = Column(Numeric(5, 4), default=0.8, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    medicine = relationship("MedicineMaster", foreign_keys=[medicine_id], back_populates="substitutes")
    substitute_medicine = relationship("MedicineMaster", foreign_keys=[substitute_medicine_id], back_populates="substituted_by")

    __table_args__ = (
        Index("idx_substitutes_medicine_id", "medicine_id"),
        Index("idx_substitutes_substitute_id", "substitute_medicine_id"),
        UniqueConstraint("medicine_id", "substitute_medicine_id", name="idx_substitutes_unique_pair"),
    )

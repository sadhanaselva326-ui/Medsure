import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text, JSON
from sqlalchemy.sql import func
from app.database import Base, GUID


class QuarantineRecord(Base):
    __tablename__ = "quarantine_record"

    quarantine_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(64), nullable=False, index=True)
    original_id = Column(String(64), nullable=True, index=True)
    identifier_or_code = Column(String(128), nullable=True, index=True)
    raw_data = Column(JSON, nullable=True)
    reason = Column(Text, nullable=False)
    quarantined_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

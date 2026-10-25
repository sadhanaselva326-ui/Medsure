import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.sql import func

from app.database import Base, GUID


class DataImportRun(Base):
    __tablename__ = "data_import_run"

    run_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    source_name = Column(String(50), nullable=False, index=True)
    adapter_name = Column(String(100), nullable=False)
    status = Column(String(30), default="running", nullable=False, index=True)  # 'running', 'completed', 'failed'
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    records_read = Column(Integer, default=0, nullable=False)
    records_imported = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_skipped = Column(Integer, default=0, nullable=False)
    errors_count = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)
    source_url_or_file = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_import_run_source_status", "source_name", "status"),
        Index("idx_import_run_created", "created_at"),
    )

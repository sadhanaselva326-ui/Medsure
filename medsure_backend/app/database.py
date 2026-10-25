import uuid
from typing import AsyncGenerator
from sqlalchemy import CHAR, TypeDecorator, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import settings


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type when available, otherwise CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


# Engine configuration
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

# If sqlite in memory or local sqlite (e.g. testing)
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

if "sqlite" in settings.DATABASE_URL:
    from sqlalchemy import event

    def _sqlite_similarity(a, b) -> float:
        """Computes real string similarity (0.0 - 1.0) on SQLite using RapidFuzz with difflib fallback."""
        if not a or not b:
            return 0.0
        s1 = str(a).lower().strip()
        s2 = str(b).lower().strip()
        if s1 == s2:
            return 1.0
        try:
            from rapidfuzz import fuzz
            return float(fuzz.ratio(s1, s2) / 100.0)
        except Exception:
            import difflib
            return float(difflib.SequenceMatcher(None, s1, s2).ratio())

    @event.listens_for(engine.sync_engine, "connect")
    def _setup_sqlite_functions(dbapi_connection, connection_record):
        dbapi_connection.create_function("to_tsvector", 2, lambda *args: "", deterministic=True)
        dbapi_connection.create_function("to_tsvector", 1, lambda *args: "", deterministic=True)
        dbapi_connection.create_function("plainto_tsquery", 2, lambda *args: "", deterministic=True)
        dbapi_connection.create_function("similarity", 2, _sqlite_similarity, deterministic=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database session to FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db_extensions():
    """Initializes required PostgreSQL extensions if connecting to PostgreSQL."""
    if "postgresql" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm";'))
            except Exception as e:
                # In restricted environments, log warning
                print(f"[Warning] Could not initialize Postgres extensions: {e}")

import asyncio
import os
# Must be set BEFORE pydantic-settings reads environment at module load
os.environ["DEBUG"] = "true"
from datetime import date, datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app
from app.config import settings as app_settings
# Patch settings instance so admin key guard always passes in tests
app_settings.DEBUG = True
from app.models.sources import DataSource
from app.models.manufacturer import Manufacturer
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.models.codes import MedicineCode
from app.models.alerts import RegulatoryAlert
from app.models.substitutes import MedicineSubstitute

# Use SQLite in-memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

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


@event.listens_for(test_engine.sync_engine, "connect")
def _setup_sqlite_functions(dbapi_connection, connection_record):
    dbapi_connection.create_function("to_tsvector", 2, lambda *args: "", deterministic=True)
    dbapi_connection.create_function("to_tsvector", 1, lambda *args: "", deterministic=True)
    dbapi_connection.create_function("plainto_tsquery", 2, lambda *args: "", deterministic=True)
    dbapi_connection.create_function("similarity", 2, _sqlite_similarity, deterministic=True)


TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        # Pre-seed standard test data
        src = DataSource(
            source_name="abdm_cdci",
            source_type="government",
            source_url="https://drugregistry.abdm.gov.in",
            verification_status="verified",
            coverage_count=120000,
        )
        session.add(src)
        await session.flush()

        mfg = Manufacturer(
            name="Micro Labs Ltd",
            address="Bangalore, Karnataka",
            gstin="29AAACM1234A1Z5",
            verification_status="verified",
            source_id=src.source_id,
        )
        session.add(mfg)
        await session.flush()

        med = Medicine(
            brand_name="Dolo 650",
            generic_name="Paracetamol",
            dosage_form="Tablet",
            strength="650 mg",
            prescription_status="otc",
            confidence_score=0.95,
            source_id=src.source_id,
            composition={"active_ingredients": [{"name": "Paracetamol IP", "quantity": "650", "unit": "mg"}], "excipients": ["Starch"]},
            therapeutic_category=["Analgesic", "Antipyretic"],
        )
        session.add(med)
        await session.flush()

        med2 = Medicine(
            brand_name="Crocin Advance",
            generic_name="Paracetamol (Fast Release)",
            dosage_form="Tablet",
            strength="500 mg",
            prescription_status="otc",
            confidence_score=0.95,
            source_id=src.source_id,
            composition={"active_ingredients": [{"name": "Paracetamol IP", "quantity": "500", "unit": "mg"}], "excipients": []},
            therapeutic_category=["Analgesic", "Antipyretic"],
        )
        session.add(med2)
        await session.flush()

        # Variant for Dolo 650
        v = MedicineVariant(
            medicine_id=med.medicine_id,
            manufacturer_id=mfg.manufacturer_id,
            pack_size=15,
            unit="tablet",
            packaging_description="Strip of 15 tablets",
            mrp=34.50,
            ceiling_price=31.20,
            batch_number="DL650201",
            expiry_date=date(2027, 8, 31),
            source_id=src.source_id,
        )
        session.add(v)
        await session.flush()

        # GTIN Code
        code = MedicineCode(
            variant_id=v.variant_id,
            gtin="08901234001011",
            barcode="8901234001011",
            source="GS1",
            verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        session.add(code)

        # Substitute
        sub = MedicineSubstitute(
            medicine_id=med.medicine_id,
            substitute_medicine_id=med2.medicine_id,
            similarity_score=0.92,
        )
        session.add(sub)

        # Sample NSQ alert on test batch (fixture; NSQ = Not of Standard Quality)
        alert = RegulatoryAlert(
            medicine_id=med.medicine_id,
            variant_id=v.variant_id,
            alert_type="nsq_alert",
            batch_number="DL650-RECALL-99",
            drug_name="Dolo 650",
            manufacturer="Micro Labs Ltd",
            alert_date=date(2026, 4, 15),
            severity="critical",
            description="Batch declared Not of Standard Quality (NSQ) — dissolution failure.",
            is_active=True,
            is_fixture=True,
            source_id=src.source_id,
        )
        session.add(alert)
        await session.commit()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()

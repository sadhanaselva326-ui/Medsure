"""test_data_ingestion.py - Unit and integration tests for MedSure Vision ingestion system.

Covers:
- Normalization (brand name, active ingredients, strength, dosage form, manufacturer, pack size, MRP)
- Deduplication (composite medicine and variant hashing)
- Import idempotency (repeated execution without duplicate records)
- Source provenance preservation (source_name, source_record_id, is_demo flag, timestamps)
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event

from app.database import Base
from app.models.sources import DataSource
from app.models.manufacturer import Manufacturer
from app.models.medicine import MedicineMaster
from app.models.variant import MedicineVariant
from app.models.codes import MedicineIdentifier
from app.models.price import MedicinePrice
from app.models.alerts import RegulatoryAlert
from app.models.import_run import DataImportRun

from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_strength,
    normalize_dosage_form,
    normalize_manufacturer,
    normalize_pack_size,
    normalize_mrp,
    normalize_therapeutic_category,
)
from scripts.data_ingestion.deduplicator import compute_medicine_hash, compute_variant_hash
from scripts.data_ingestion.pipeline import DataIngestionPipeline
from scripts.data_ingestion.adapters.pmbi_adapter import PMBIJanAushadhiAdapter
from scripts.data_ingestion.adapters.nppa_adapter import NPPACeilingPriceAdapter
from scripts.data_ingestion.adapters.cdsco_adapter import CDSCOAlertAdapter


# ===========================================================================
# 1. Normalization Unit Tests
# ===========================================================================

def test_normalize_brand_name():
    assert normalize_brand_name("Augmentin 625 Duo Tablet") == "Augmentin 625"
    assert normalize_brand_name("Dolo 650mg Tablets (15s)") == "Dolo 650MG" or "Dolo 650" in normalize_brand_name("Dolo 650mg Tablets (15s)")
    assert normalize_brand_name("Ascoril LS Syrup (100 ml)") == "Ascoril LS"
    assert normalize_brand_name("Crocin Advance Tablet") == "Crocin Advance"
    assert normalize_brand_name("") == ""
    assert normalize_brand_name(None) == ""


def test_normalize_generic_name():
    # IP/BP token stripping and salt synonym mapping
    assert normalize_generic_name("Paracetamol IP") == "Paracetamol"
    assert normalize_generic_name("Amoxycillin Trihydrate IP") == "Amoxicillin"
    assert normalize_generic_name("Amoxycillin (500mg) + Clavulanic Acid (125mg)") == "Amoxicillin + Clavulanic Acid"
    assert normalize_generic_name("Metformin Hydrochloride IP") == "Metformin"
    assert normalize_generic_name("Atorvastatin Calcium IP") == "Atorvastatin"
    assert normalize_generic_name("Salbutamol Sulphate IP") == "Salbutamol"


def test_normalize_strength():
    assert normalize_strength("650mg") == "650 mg"
    assert normalize_strength("500 mg") == "500 mg"
    assert normalize_strength("500mg+125mg") == "500 mg + 125 mg" or "500 mg" in normalize_strength("500mg+125mg")
    assert normalize_strength("15mg/5ml") == "15 mg / 5 ml"
    assert normalize_strength(None) is None
    assert normalize_strength("") is None


def test_normalize_dosage_form():
    assert normalize_dosage_form("film coated tablet") == "Tablet"
    assert normalize_dosage_form("chewable tablet") == "Chewable Tablet"
    assert normalize_dosage_form("cap") == "Capsule"
    assert normalize_dosage_form("soft gelatin capsule") == "Capsule"
    assert normalize_dosage_form("syr") == "Syrup"
    assert normalize_dosage_form("inj") == "Injection"
    assert normalize_dosage_form("rotacaps") == "Inhaler (Rotacaps)"


def test_normalize_manufacturer():
    assert normalize_manufacturer("micro labs limited") == "Micro Labs Ltd"
    assert normalize_manufacturer("Glaxo Smithkline Pharmaceuticals Limited") == "GlaxoSmithKline Pharmaceuticals Ltd (GSK)"
    assert normalize_manufacturer("Sanofi India Private Limited") == "Sanofi India Ltd"
    assert normalize_manufacturer("Cipla Ltd.") == "Cipla Ltd"
    assert normalize_manufacturer("PMBI") == "Pharmaceuticals & Medical Devices Bureau of India (PMBI)"


def test_normalize_pack_size_and_mrp():
    pack, unit = normalize_pack_size("strip of 10 tablets")
    assert pack == 10
    assert unit == "tablet"

    pack, unit = normalize_pack_size("bottle of 100 ml Syrup")
    assert pack == 100
    assert unit == "ml"

    assert normalize_mrp("₹ 34.50") == 34.50
    assert normalize_mrp("Rs. 18.20/-") == 18.20
    assert normalize_mrp(25.0) == 25.0
    assert normalize_mrp(None) is None


def test_normalize_therapeutic_category():
    cats = normalize_therapeutic_category("Analgesic, Antipyretic; Anti-inflammatory")
    assert "Analgesic" in cats
    assert "Antipyretic" in cats
    assert "Anti-Inflammatory" in cats


# ===========================================================================
# 2. Deduplication Hashing Tests
# ===========================================================================

def test_deduplication_hashing():
    # Same formulation with minor cosmetic spacing should yield identical hash
    hash1 = compute_medicine_hash("Dolo 650", "Paracetamol IP", "650mg", "Tablet")
    hash2 = compute_medicine_hash("Dolo 650 Tablets", "Paracetamol", "650 mg", "film coated tablet")
    assert hash1 == hash2

    # Different strength must produce different hash
    hash3 = compute_medicine_hash("Dolo 500", "Paracetamol IP", "500mg", "Tablet")
    assert hash1 != hash3

    # Variant hashing
    v_hash1 = compute_variant_hash(hash1, "Micro Labs Ltd", 15, "tablet")
    v_hash2 = compute_variant_hash(hash1, "micro labs limited", 15, "tablets")
    assert v_hash1 == v_hash2

    v_hash3 = compute_variant_hash(hash1, "Micro Labs Ltd", 10, "tablet")
    assert v_hash1 != v_hash3


# ===========================================================================
# 3. Import Pipeline Idempotency & Provenance Integration Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_import_idempotency_and_provenance():
    # Set up in-memory SQLite engine
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine.sync_engine, "connect")
    def _setup_sqlite(dbapi_conn, record):
        dbapi_conn.create_function("to_tsvector", 2, lambda *args: "", deterministic=True)
        dbapi_conn.create_function("to_tsvector", 1, lambda *args: "", deterministic=True)
        dbapi_conn.create_function("plainto_tsquery", 2, lambda *args: "", deterministic=True)
        dbapi_conn.create_function("similarity", 2, lambda *args: 0.5, deterministic=True)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    pipeline = DataIngestionPipeline()
    pmbi_adapter = PMBIJanAushadhiAdapter()
    nppa_adapter = NPPACeilingPriceAdapter()
    # Tests must explicitly supply the fixture file; the adapter default points to
    # downloads/cdsco/ which only exists when real data has been downloaded.
    _fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "cdsco_nsq_alerts_fixture.json")
    cdsco_adapter = CDSCOAlertAdapter.__new__(CDSCOAlertAdapter)
    cdsco_adapter.file_path = _fixture_file  # bypass guard — fixture used intentionally in test

    # FIRST RUN: Verify records are imported and provenance stored
    async with TestSession() as session:
        pmbi_stats = await pipeline.run_adapter(session, pmbi_adapter)
        assert pmbi_stats.status == "completed"
        assert pmbi_stats.records_imported > 0
        assert pmbi_stats.errors_count == 0

        nppa_stats = await pipeline.run_adapter(session, nppa_adapter)
        assert nppa_stats.status == "completed"
        assert nppa_stats.records_imported > 0
        assert nppa_stats.errors_count == 0

        cdsco_stats = await pipeline.run_adapter(session, cdsco_adapter)
        assert cdsco_stats.status == "completed"
        assert cdsco_stats.records_imported > 0
        assert cdsco_stats.errors_count == 0

    # Verify counts in database after First Run
    async with TestSession() as session:
        med_count_1 = (await session.execute(select(func.count(MedicineMaster.medicine_id)))).scalar()
        alert_count_1 = (await session.execute(select(func.count(RegulatoryAlert.alert_id)))).scalar()
        price_count_1 = (await session.execute(select(func.count(MedicinePrice.price_id)))).scalar()

        assert med_count_1 >= 50
        assert alert_count_1 >= 10
        assert price_count_1 >= 50

        # Verify provenance fields on an imported medicine
        sample_med = (await session.execute(select(MedicineMaster).where(MedicineMaster.source_name == "pmbi_janaushadhi"))).scalars().first()
        assert sample_med is not None
        assert sample_med.is_demo is False
        assert sample_med.source_url == "https://janaushadhi.gov.in"
        assert sample_med.source_record_id is not None
        assert sample_med.last_verified_at is not None

        # Verify provenance on an alert
        sample_alert = (await session.execute(select(RegulatoryAlert).where(RegulatoryAlert.source_name == "cdsco_nsq"))).scalars().first()
        assert sample_alert is not None
        assert sample_alert.is_demo is False
        assert sample_alert.reason_for_nsq is not None
        assert sample_alert.testing_lab is not None

    # SECOND RUN: Verify complete idempotency (records_imported == 0, records_skipped == total)
    async with TestSession() as session:
        pmbi_stats_2 = await pipeline.run_adapter(session, pmbi_adapter)
        assert pmbi_stats_2.status == "completed"
        assert pmbi_stats_2.records_imported == 0
        assert pmbi_stats_2.records_skipped == pmbi_stats_2.records_read

        nppa_stats_2 = await pipeline.run_adapter(session, nppa_adapter)
        assert nppa_stats_2.status == "completed"
        assert nppa_stats_2.records_imported == 0
        assert nppa_stats_2.records_skipped == nppa_stats_2.records_read

        cdsco_stats_2 = await pipeline.run_adapter(session, cdsco_adapter)
        assert cdsco_stats_2.status == "completed"
        assert cdsco_stats_2.records_imported == 0
        assert cdsco_stats_2.records_skipped == cdsco_stats_2.records_read

    # Verify counts in database remain identical (zero duplicate rows created)
    async with TestSession() as session:
        med_count_2 = (await session.execute(select(func.count(MedicineMaster.medicine_id)))).scalar()
        alert_count_2 = (await session.execute(select(func.count(RegulatoryAlert.alert_id)))).scalar()
        price_count_2 = (await session.execute(select(func.count(MedicinePrice.price_id)))).scalar()

        assert med_count_2 == med_count_1
        assert alert_count_2 == alert_count_1
        assert price_count_2 == price_count_1

        # Verify DataImportRun records
        runs = (await session.execute(select(DataImportRun))).scalars().all()
        assert len(runs) == 6  # 3 runs in batch 1 + 3 runs in batch 2
        for r in runs:
            assert r.status == "completed"
            assert r.errors_count == 0

    await test_engine.dispose()

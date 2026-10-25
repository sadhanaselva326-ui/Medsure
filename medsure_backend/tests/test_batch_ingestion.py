import pytest
import os
import tempfile
import csv
from uuid import uuid4
from datetime import datetime, timezone

from app.utils.helpers import (
    parse_pack_size_label,
    clean_salt_name,
    extract_strength_string,
    build_medicine_dedup_keys,
)
from app.models.sources import DataSource
from app.models.medicine import Medicine
from app.models.variant import MedicineVariant
from app.schemas.ingestion import IngestRequest, IngestStats
from app.services.ingestion_service import ingest_dataset


def test_parse_pack_size_label():
    # Tablet strip
    qty, unit, desc = parse_pack_size_label("strip of 10 tablets")
    assert qty == 10
    assert unit == "tablet"
    assert desc == "strip of 10 tablets"

    # Syrup bottle
    qty, unit, desc = parse_pack_size_label("bottle of 100 ml syrup")
    assert qty == 100
    assert unit == "ml"

    # Capsule box
    qty, unit, desc = parse_pack_size_label("box of 15 capsules")
    assert qty == 15
    assert unit == "capsule"

    # Inhaler doses
    qty, unit, desc = parse_pack_size_label("inhaler of 200 doses")
    assert qty == 200
    assert unit == "doses"

    # Tube ointment
    qty, unit, desc = parse_pack_size_label("tube of 30 gm ointment")
    assert qty == 30
    assert unit == "gm"

    # Numeric only with default dosage form
    qty, unit, desc = parse_pack_size_label("15", default_dosage_form="Capsule")
    assert qty == 15
    assert unit == "capsule"

    # Unparseable label: does not invent fake values
    qty, unit, desc = parse_pack_size_label("Special Presentation Pack")
    assert qty is None
    assert unit is None
    assert desc == "Special Presentation Pack"

    # Empty label
    qty, unit, desc = parse_pack_size_label(None)
    assert qty is None
    assert unit is None
    assert desc is None


def test_clean_salt_name_and_strength():
    # Remove strength in parentheses
    salt = clean_salt_name("Paracetamol (650mg)")
    assert salt == "paracetamol"

    # Remove IP / BP markers
    salt2 = clean_salt_name("Paracetamol IP 500mg")
    assert salt2 == "paracetamol"

    # Multi-ingredient
    salt3 = clean_salt_name("Amoxicillin (500mg) + Potassium Clavulanate (125mg)")
    assert "amoxicillin" in salt3
    assert "clavulanate" in salt3

    # Extract strength string
    s1 = extract_strength_string("Paracetamol (650mg)")
    assert s1 == "650 mg"

    s2 = extract_strength_string(None, fallback_text="Combiflam Ibuprofen 400mg + Paracetamol 325mg")
    assert "400mg + 325mg" in s2 or "400 mg" in s2


def test_build_medicine_dedup_keys():
    keys = build_medicine_dedup_keys(
        brand_name="Dolo 650",
        generic_name="Paracetamol (650mg)",
        dosage_form="Tablet",
        strength="650 mg",
    )
    assert "dolo 650|paracetamol|tablet|650 mg" in keys
    assert "dolo 650|paracetamol|tablet" in keys
    assert "dolo 650|paracetamol" in keys


@pytest.mark.asyncio
async def test_ingestion_deduplication_and_variants(db_session):
    """Verifies:

    1. Seed medicine 'Dolo 650' is reused, not duplicated.
    2. Multiple pack sizes of same medicine become variants.
    3. Syrups and liquids parse pack size/unit correctly.
    4. Missing optional fields are handled safely.
    5. Invalid pricing is handled safely.
    6. No fake barcodes/GTINs are generated.
    """
    # Grab the existing test data source from db_session
    from sqlalchemy import select
    res = await db_session.execute(select(DataSource))
    source = res.scalars().first()
    assert source is not None

    test_records = [
        # 1. Exact duplicate of existing seed medicine Dolo 650 (pack size 15 already exists)
        {
            "name": "Dolo 650",
            "composition": "Paracetamol (650mg)",
            "manufacturer_name": "Micro Labs Ltd",
            "price": "₹34.50",
            "type": "Tablet",
            "pack_size_label": "strip of 15 tablets",
        },
        # 2. Second pack size of existing seed medicine Dolo 650 (new variant: 30 tablets)
        {
            "name": "Dolo 650 Tablet",
            "composition": "Paracetamol",
            "manufacturer_name": "Micro Labs Ltd",
            "price": "65.00",
            "type": "Tablet",
            "pack_size_label": "bottle of 30 tablets",
        },
        # 3. New medicine - Pack size 1 (10 tablets)
        {
            "name": "Allegra 120",
            "composition": "Fexofenadine Hydrochloride (120mg)",
            "manufacturer_name": "Sanofi India Ltd",
            "price": "180.00",
            "type": "Tablet",
            "pack_size_label": "strip of 10 tablets",
        },
        # 4. Same new medicine Allegra 120 - Pack size 2 (15 tablets) -> should NOT create duplicate parent medicine
        {
            "name": "Allegra 120",
            "composition": "Fexofenadine Hydrochloride (120mg)",
            "manufacturer_name": "Sanofi India Ltd",
            "price": "260.00",
            "type": "Tablet",
            "pack_size_label": "strip of 15 tablets",
        },
        # 5. Liquid/Syrup example
        {
            "name": "Ascoril D Plus",
            "composition": "Dextromethorphan + Chlorpheniramine + Phenylephrine",
            "manufacturer_name": "Glenmark Pharmaceuticals Ltd",
            "price": "125.00",
            "type": "Syrup",
            "pack_size_label": "bottle of 100 ml",
        },
        # 6. Inhaler example
        {
            "name": "Asthalin Inhaler",
            "composition": "Salbutamol (100mcg)",
            "manufacturer_name": "Cipla Ltd",
            "price": "165.00",
            "type": "Inhaler",
            "pack_size_label": "inhaler of 200 doses",
        },
        # 7. Row with missing optional fields (no price, no manufacturer, no dosage form)
        {
            "name": "Zincovit",
            "composition": "Multivitamins and Minerals",
            "pack_size_label": "strip of 15 tablets",
        },
        # 8. Row with malformed price and unparseable pack size label
        {
            "name": "Revital H",
            "composition": "Ginseng + 10 Vitamins + 9 Minerals",
            "manufacturer_name": "Sun Pharmaceutical Industries Ltd",
            "price": "InvalidPriceString",
            "type": "Capsule",
            "pack_size_label": "Special Tin Container",
        },
        # 9. Row with genuine barcode provided
        {
            "name": "Meftal Spas",
            "composition": "Mefenamic Acid + Dicyclomine",
            "manufacturer_name": "Blue Cross Laboratories",
            "price": "52.00",
            "type": "Tablet",
            "pack_size_label": "strip of 10 tablets",
            "barcode": "8901234567890",
        },
        # 10. Invalid row (missing brand and generic) -> should be skipped safely
        {
            "name": "",
            "composition": "",
            "price": "100.00",
        },
    ]

    req = IngestRequest(
        source_id=source.source_id,
        raw_data=test_records,
        batch_size=5,  # test batch processing
    )

    stats: IngestStats = await ingest_dataset(db_session, req)

    # Validate high-level stats
    assert stats.total_processed == 10
    assert stats.skipped == 1  # row 10 was skipped
    assert stats.failed == 0   # no hard failures

    # Dolo 650 rows (rows 1 & 2):
    # Both should be recognized as existing Dolo 650 (updated_reused >= 2)
    assert stats.updated_reused >= 2

    # Allegra 120 (rows 3 & 4):
    # First Allegra 120 row creates 1 medicine. Second Allegra 120 row reuses that medicine.
    # Total new medicines should be: Allegra 120 (1) + Ascoril D (1) + Asthalin (1) + Zincovit (1) + Revital H (1) + Meftal Spas (1) = 6
    assert stats.imported == 6

    # Verify Dolo 650 in database: only ONE Dolo 650 medicine parent record
    dolo_stmt = select(Medicine).where(Medicine.brand_name.ilike("Dolo 650"))
    dolo_records = (await db_session.execute(dolo_stmt)).scalars().all()
    assert len(dolo_records) == 1, f"Expected 1 Dolo 650 medicine record, found {len(dolo_records)}"

    dolo_med = dolo_records[0]
    # Verify variants of Dolo 650:
    var_stmt = select(MedicineVariant).where(MedicineVariant.medicine_id == dolo_med.medicine_id)
    dolo_variants = (await db_session.execute(var_stmt)).scalars().all()
    pack_sizes = [v.pack_size for v in dolo_variants]
    # Original test fixture had 15 tablets; ingestion added 30 tablets
    assert 15 in pack_sizes
    assert 30 in pack_sizes
    # Row 1 tried to insert 15 tablets again -> should NOT create a duplicate 15-pack variant!
    count_15 = pack_sizes.count(15)
    assert count_15 == 1, f"Expected exactly one 15-tablet variant for Dolo 650, found {count_15}"

    # Verify Allegra 120: exactly ONE medicine with TWO variants (10 and 15)
    allegra_stmt = select(Medicine).where(Medicine.brand_name == "Allegra 120")
    allegra_meds = (await db_session.execute(allegra_stmt)).scalars().all()
    assert len(allegra_meds) == 1, f"Expected 1 Allegra 120 medicine, found {len(allegra_meds)}"

    allegra_vars = (await db_session.execute(
        select(MedicineVariant).where(MedicineVariant.medicine_id == allegra_meds[0].medicine_id)
    )).scalars().all()
    assert len(allegra_vars) == 2, f"Expected 2 variants for Allegra 120, found {len(allegra_vars)}"
    allegra_packs = {v.pack_size for v in allegra_vars}
    assert allegra_packs == {10, 15}

    # Verify Syrup parsing (Ascoril D Plus)
    ascoril_stmt = select(Medicine).where(Medicine.brand_name == "Ascoril D Plus")
    ascoril = (await db_session.execute(ascoril_stmt)).scalars().first()
    assert ascoril is not None
    ascoril_var = (await db_session.execute(
        select(MedicineVariant).where(MedicineVariant.medicine_id == ascoril.medicine_id)
    )).scalars().first()
    assert ascoril_var.pack_size == 100
    assert ascoril_var.unit == "ml"

    # Verify Asthalin Inhaler (pack_size: 200, unit: doses)
    asthalin_stmt = select(Medicine).where(Medicine.brand_name == "Asthalin Inhaler")
    asthalin = (await db_session.execute(asthalin_stmt)).scalars().first()
    assert asthalin is not None
    asthalin_var = (await db_session.execute(
        select(MedicineVariant).where(MedicineVariant.medicine_id == asthalin.medicine_id)
    )).scalars().first()
    assert asthalin_var.pack_size == 200
    assert asthalin_var.unit == "doses"

    # Verify Revital H (unparseable pack label preserved in packaging_description)
    revital_stmt = select(Medicine).where(Medicine.brand_name == "Revital H")
    revital = (await db_session.execute(revital_stmt)).scalars().first()
    assert revital is not None
    revital_var = (await db_session.execute(
        select(MedicineVariant).where(MedicineVariant.medicine_id == revital.medicine_id)
    )).scalars().first()
    assert revital_var.pack_size is None
    assert revital_var.mrp is None  # invalid price was safely set to None
    assert revital_var.packaging_description == "Special Tin Container"

    # Verify barcode on Meftal Spas
    meftal_stmt = select(Medicine).where(Medicine.brand_name == "Meftal Spas")
    meftal = (await db_session.execute(meftal_stmt)).scalars().first()
    assert meftal is not None
    from app.models.codes import MedicineCode
    code_res = (await db_session.execute(
        select(MedicineCode)
        .join(MedicineVariant)
        .where(MedicineVariant.medicine_id == meftal.medicine_id)
    )).scalars().first()
    assert code_res is not None
    assert code_res.barcode == "8901234567890"

    # Verify NO fake barcodes were created for other medicines
    zincovit_stmt = select(Medicine).where(Medicine.brand_name == "Zincovit")
    zincovit = (await db_session.execute(zincovit_stmt)).scalars().first()
    z_codes = (await db_session.execute(
        select(MedicineCode)
        .join(MedicineVariant)
        .where(MedicineVariant.medicine_id == zincovit.medicine_id)
    )).scalars().all()
    assert len(z_codes) == 0, "No codes should be created when row lacks barcode/gtin"

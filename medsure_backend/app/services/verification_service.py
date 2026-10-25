import re
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.codes import MedicineIdentifier
from app.models.medicine import MedicineMaster
from app.models.variant import MedicineVariant
from app.models.manufacturer import Manufacturer
from app.models.sources import DataSource
from app.models.alerts import RegulatoryAlert
from app.schemas.verification import (
    ExtractedFields,
    MatchedMedicineItem,
    RiskAssessment,
    ScanAnalyzeRequest,
    ScanAnalyzeResponse,
    MedicineVerifyRequest,
    MedicineVerifyResponse,
    Layer1Result,
    Layer2Result,
    Layer3Result,
    PerLayerResults,
    FieldMatchResult,
)
from app.schemas.alerts import RegulatoryAlertRead
from app.utils.helpers import (
    calculate_string_similarity,
    normalize_text,
    extract_strength_and_unit,
    clean_salt_name,
)

DISCLAIMER_TEXT = (
    "MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. "
    "Consult a pharmacist."
)

STATUS_MATCH = "Matches a catalogue record"
STATUS_NEEDS_VERIFY = "Needs verification"
STATUS_ALERT_FOUND = "Regulatory alert found"
STATUS_NO_MATCH = "No matching record in the MedSure catalogue"
STATUS_INSUFFICIENT = "Insufficient input"


def parse_ocr_text_to_fields(ocr_text: Optional[str], existing_fields: Optional[ExtractedFields] = None) -> ExtractedFields:
    """Extracts structured fields from raw OCR text using regex heuristics."""
    fields = existing_fields.model_copy() if existing_fields else ExtractedFields()

    if not ocr_text:
        return fields

    text = ocr_text.strip()

    # Extract Batch Number
    if not fields.batch_number:
        batch_m = re.search(r"(?:batch|b\.?\s*no\.?)[:\s]+([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if batch_m:
            fields.batch_number = batch_m.group(1).strip()

    # Extract Expiry
    if not fields.expiry_date:
        exp_m = re.search(
            r"(?:exp|expiry|exp\.?\s*date)[:\s]+([0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}[/-][0-9]{1,2})",
            text,
            re.IGNORECASE,
        )
        if exp_m:
            fields.expiry_date = exp_m.group(1).strip()

    # Extract Manufacturer
    if not fields.manufacturer:
        mfg_m = re.search(
            r"(?:mfg|manufactured\s+by|mkt\s+by)[:\s]+(.*?)(?=\s+(?:batch|b\.?\s*no|exp|expiry|mrp|lic|pkg|rs|\$|₹)|$)",
            text,
            re.IGNORECASE,
        )
        if mfg_m and mfg_m.group(1).strip():
            fields.manufacturer = mfg_m.group(1).strip()

    # Extract Strength: e.g. 500 mg, 650mg, 10mg
    if not fields.strength:
        val, unit = extract_strength_and_unit(text)
        if val and unit:
            fields.strength = f"{val} {unit}"

    # Extract MRP
    if not fields.mrp:
        mrp_m = re.search(r"(?:mrp|rs\.?|₹)[:\s]*([0-9]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if mrp_m:
            try:
                fields.mrp = float(mrp_m.group(1))
            except ValueError:
                pass

    # Extract Brand / Generic if not present
    if not fields.brand_name:
        pre_mfg = re.split(r"(?:mfg|manufactured|mkt|batch|exp|b\.no)", text, flags=re.IGNORECASE)[0].strip()
        tokens = pre_mfg.split()
        if len(tokens) >= 2 and tokens[1].isdigit():
            fields.brand_name = f"{tokens[0]} {tokens[1]}"
        elif tokens:
            fields.brand_name = tokens[0]

    return fields


COMMON_PREFIXES = ("jan aushadhi", "nppa ceiling", "dpco ceiling", "pmbi")


def strip_brand_prefix(text: Optional[str]) -> str:
    if not text:
        return ""
    norm = normalize_text(text)
    for p in COMMON_PREFIXES:
        if norm.startswith(p):
            norm = norm[len(p):].strip()
    return norm


def compute_similarity(s1: Optional[str], s2: Optional[str]) -> float:
    """Computes similarity ratio using RapidFuzz with difflib fallback."""
    if not s1 or not s2:
        return 0.0
    c1 = normalize_text(str(s1))
    c2 = normalize_text(str(s2))
    if c1 == c2:
        return 1.0

    p1 = strip_brand_prefix(c1)
    p2 = strip_brand_prefix(c2)

    try:
        from rapidfuzz import fuzz
        if p1 and p2 and (p1 != c1 or p2 != c2):
            return float(fuzz.token_sort_ratio(p1, p2) / 100.0)
        return float(fuzz.token_set_ratio(c1, c2) / 100.0)
    except Exception:
        import difflib
        t1 = p1 if p1 else c1
        t2 = p2 if p2 else c2
        return float(difflib.SequenceMatcher(None, t1, t2).ratio())


async def analyze_scan_or_query(
    session: AsyncSession,
    payload: ScanAnalyzeRequest,
) -> ScanAnalyzeResponse:
    """Production 3-Layer Verification Engine:

    Layer 1: Identifier (Barcode / GTIN lookup)
    Layer 2: Details & Pricing (Fuzzy name, strength, form, manufacturer, and price check)
    Layer 3: Batch Regulatory Alerts (Lookup in CDSCO regulatory alerts)

    Maps status exclusively to the 5 allowed labels:
      - "Matches a catalogue record"
      - "Needs verification"
      - "Regulatory alert found"
      - "No matching record in the MedSure catalogue"
      - "Insufficient input"
    """
    # 0. Coalesce input fields (top-level overrides nested extracted_fields)
    ext = payload.extracted_fields or ExtractedFields()
    if payload.ocr_text:
        ext = parse_ocr_text_to_fields(payload.ocr_text, ext)

    brand_input = payload.name or payload.brand_name or ext.brand_name
    generic_input = payload.ingredients or payload.generic_name or payload.composition or ext.generic_name or ext.ingredients
    strength_input = payload.strength or ext.strength
    dosage_form_input = payload.dosage_form or ext.dosage_form
    mfg_input = payload.manufacturer or ext.manufacturer
    batch_input = (payload.batch_number or ext.batch_number or "").strip()
    mrp_input = payload.mrp or ext.mrp
    barcode_input = (payload.barcode or payload.gtin or "").strip()

    # 1. Check for Insufficient Input
    has_any_input = any([
        brand_input,
        generic_input,
        strength_input,
        dosage_form_input,
        mfg_input,
        batch_input,
        barcode_input,
        payload.ocr_text,
    ])

    if not has_any_input:
        per_layer = PerLayerResults(
            layer_1_identifier=Layer1Result(
                layer="Layer 1: Identifier",
                checked=False,
                status="SKIPPED",
                details="No barcode or GTIN provided.",
            ),
            layer_2_details=Layer2Result(
                layer="Layer 2: Details & Pricing",
                checked=False,
                status="SKIPPED",
            ),
            layer_3_batch_alerts=Layer3Result(
                layer="Layer 3: Batch Regulatory Alerts",
                checked=False,
                status="SKIPPED",
                details="No batch number provided.",
            ),
        )
        return ScanAnalyzeResponse(
            status=STATUS_INSUFFICIENT,
            confidence=None,
            reasons=["Insufficient input provided for verification. Please provide a medicine name, barcode, or batch number."],
            matched_record=None,
            matched_medicines=[],
            per_layer_results=per_layer,
            mismatched_fields=[],
            regulatory_alerts=[],
            evidence_links=[],
            disclaimer=DISCLAIMER_TEXT,
            risk_assessment=RiskAssessment(
                overall_risk="high",
                flags=["INSUFFICIENT_INPUT"],
                recommendation=STATUS_INSUFFICIENT,
                explanation="Insufficient input provided for verification.",
            ),
            recommendation=STATUS_INSUFFICIENT,
        )

    # 2. LAYER 1: Identifier match (barcode / GTIN)
    layer1 = Layer1Result(layer="Layer 1: Identifier")
    primary_medicine: Optional[MedicineMaster] = None
    primary_variant: Optional[MedicineVariant] = None
    confidence: Optional[float] = None

    if barcode_input:
        layer1.checked = True
        layer1.identifier_value = barcode_input

        # Check for malformed barcode
        if not re.match(r"^[A-Za-z0-9_-]{4,20}$", barcode_input):
            layer1.status = "INVALID"
            layer1.details = f"Malformed identifier '{barcode_input}'"
        else:
            id_stmt = (
                select(MedicineIdentifier)
                .options(
                    selectinload(MedicineIdentifier.variant)
                    .selectinload(MedicineVariant.medicine)
                    .selectinload(MedicineMaster.source),
                    selectinload(MedicineIdentifier.variant).selectinload(MedicineVariant.manufacturer),
                )
                .where(
                    or_(
                        MedicineIdentifier.gtin == barcode_input,
                        MedicineIdentifier.barcode == barcode_input,
                        MedicineIdentifier.identifier_value == barcode_input,
                        func.lower(MedicineIdentifier.identifier_value) == barcode_input.lower(),
                    )
                )
            )
            id_match = (await session.execute(id_stmt)).scalars().first()

            if id_match and id_match.variant and id_match.variant.medicine:
                primary_variant = id_match.variant
                primary_medicine = primary_variant.medicine
                confidence = 1.0
                layer1.status = "MATCH"
                layer1.identifier_type = id_match.identifier_type
                layer1.details = f"Exact match found in MedSure catalogue ({id_match.identifier_type}: {barcode_input})"
            else:
                layer1.status = "NO_MATCH"
                layer1.details = f"Identifier '{barcode_input}' not found in catalogue"
    else:
        layer1.checked = False
        layer1.status = "SKIPPED"
        layer1.details = "No barcode or GTIN provided."

    # 3. LAYER 2: Details Matching (Fuzzy search & per-field verification)
    layer2 = Layer2Result(layer="Layer 2: Details & Pricing")
    field_results: Dict[str, FieldMatchResult] = {}
    mismatched_fields: List[str] = []

    # If Layer 1 did not find candidate, perform fuzzy search over catalogue
    if not primary_medicine and (brand_input or generic_input or payload.ocr_text):
        layer2.checked = True
        cand_stmt = (
            select(MedicineMaster)
            .options(
                selectinload(MedicineMaster.variants).selectinload(MedicineVariant.manufacturer),
                selectinload(MedicineMaster.source),
            )
            .where(MedicineMaster.is_discontinued == False)
        )
        cand_res = await session.execute(cand_stmt)
        all_candidates = cand_res.scalars().all()

        salt_stopwords = {
            "sodium", "potassium", "calcium", "hydrochloride", "hcl", "phosphate",
            "sulphate", "sulfate", "acetate", "maleate", "citrate", "tartrate",
            "tablet", "tablets", "capsule", "capsules", "injection", "syrup",
            "suspension", "drops", "eye", "ointment", "cream", "gel", "solution",
            "oral", "ip", "bp", "usp", "mcg", "mg", "ml", "gm"
        }
        # Compose the primary search text from brand or generic input
        search_text = normalize_text(
            brand_input or generic_input or (payload.ocr_text or "")
        ).lower()
        best_score: float = 0.0
        best_cand: Optional[MedicineMaster] = None
        search_core_tokens = set(re.findall(r"[a-z]{4,}", search_text)) - salt_stopwords

        for cand in all_candidates:
            cand_b_tokens = set(re.findall(r"[a-z]{4,}", (cand.brand_name or "").lower())) - salt_stopwords
            cand_g_tokens = set(re.findall(r"[a-z]{4,}", (cand.generic_name or "").lower())) - salt_stopwords
            cand_core = cand_b_tokens | cand_g_tokens

            # Candidate MUST share at least one core pharmaceutical active ingredient token (len >= 4)
            if search_core_tokens and cand_core and not (search_core_tokens & cand_core):
                continue

            # Score name against brand & generic
            score_b = compute_similarity(search_text, cand.brand_name)
            score_g = compute_similarity(search_text, cand.generic_name)
            base_score = max(score_b, score_g)

            # Bonus for strength match
            if strength_input and cand.strength:
                val1, _ = extract_strength_and_unit(strength_input)
                val2, _ = extract_strength_and_unit(cand.strength)
                if val1 and val2 and val1 == val2:
                    base_score = min(1.0, base_score + 0.15)
                elif val1 and val2 and val1 != val2 and base_score > 0.5:
                    # Penalize strength discrepancy
                    base_score = max(0.2, base_score - 0.25)

            if base_score > best_score:
                best_score = base_score
                best_cand = cand

        if best_cand and best_score >= 0.70:
            primary_medicine = best_cand
            confidence = round(best_score, 2)
            layer2.score = confidence
            if primary_medicine.variants:
                primary_variant = primary_medicine.variants[0]
        else:
            primary_medicine = None
            primary_variant = None
            confidence = None
            layer2.status = "NOT_CHECKED"
            layer2.score = None
            layer2.details = "No matching medicine found in MedSure catalogue."

    # If candidate is matched (either from Layer 1 or Layer 2), compare per-field consistency
    if primary_medicine:
        layer2.checked = True

        # Field: brand_name / name
        cat_brand = primary_medicine.brand_name or ""
        if brand_input:
            sim = compute_similarity(brand_input, cat_brand)
            # Also accept generic match for generics
            if sim < 0.60 and primary_medicine.generic_name:
                sim = max(sim, compute_similarity(brand_input, primary_medicine.generic_name))
            if sim >= 0.60:
                field_results["name"] = FieldMatchResult(field="name", input_value=brand_input, catalog_value=cat_brand, status="match")
            else:
                field_results["name"] = FieldMatchResult(field="name", input_value=brand_input, catalog_value=cat_brand, status="mismatch")
                mismatched_fields.append("name")
        else:
            field_results["name"] = FieldMatchResult(field="name", input_value=None, catalog_value=cat_brand, status="missing")

        # Field: generic_name / ingredients
        cat_generic = primary_medicine.generic_name or ""
        if generic_input:
            sim = compute_similarity(generic_input, cat_generic)
            if sim >= 0.60:
                field_results["ingredients"] = FieldMatchResult(field="ingredients", input_value=generic_input, catalog_value=cat_generic, status="match")
            else:
                field_results["ingredients"] = FieldMatchResult(field="ingredients", input_value=generic_input, catalog_value=cat_generic, status="mismatch")
                mismatched_fields.append("ingredients")
        else:
            field_results["ingredients"] = FieldMatchResult(field="ingredients", input_value=None, catalog_value=cat_generic, status="missing")

        # Field: strength
        cat_strength = primary_medicine.strength or ""
        if strength_input:
            if cat_strength:
                val1, unit1 = extract_strength_and_unit(strength_input)
                val2, unit2 = extract_strength_and_unit(cat_strength)
                if val1 and val2 and val1 == val2:
                    field_results["strength"] = FieldMatchResult(field="strength", input_value=strength_input, catalog_value=cat_strength, status="match")
                else:
                    field_results["strength"] = FieldMatchResult(field="strength", input_value=strength_input, catalog_value=cat_strength, status="mismatch")
                    mismatched_fields.append("strength")
            else:
                field_results["strength"] = FieldMatchResult(field="strength", input_value=strength_input, catalog_value=None, status="missing")
        else:
            field_results["strength"] = FieldMatchResult(field="strength", input_value=None, catalog_value=cat_strength or None, status="missing")

        # Field: dosage_form
        cat_form = primary_medicine.dosage_form or ""
        if dosage_form_input:
            if cat_form:
                if normalize_text(dosage_form_input) in normalize_text(cat_form) or normalize_text(cat_form) in normalize_text(dosage_form_input):
                    field_results["dosage_form"] = FieldMatchResult(field="dosage_form", input_value=dosage_form_input, catalog_value=cat_form, status="match")
                else:
                    field_results["dosage_form"] = FieldMatchResult(field="dosage_form", input_value=dosage_form_input, catalog_value=cat_form, status="mismatch")
                    mismatched_fields.append("dosage_form")
            else:
                field_results["dosage_form"] = FieldMatchResult(field="dosage_form", input_value=dosage_form_input, catalog_value=None, status="missing")
        else:
            field_results["dosage_form"] = FieldMatchResult(field="dosage_form", input_value=None, catalog_value=cat_form or None, status="missing")

        # Field: manufacturer
        cat_mfg = (primary_variant.manufacturer.name if primary_variant and primary_variant.manufacturer else None)
        if mfg_input:
            if cat_mfg:
                sim = compute_similarity(mfg_input, cat_mfg)
                if sim >= 0.65:
                    field_results["manufacturer"] = FieldMatchResult(field="manufacturer", input_value=mfg_input, catalog_value=cat_mfg, status="match")
                else:
                    field_results["manufacturer"] = FieldMatchResult(field="manufacturer", input_value=mfg_input, catalog_value=cat_mfg, status="mismatch")
                    mismatched_fields.append("manufacturer")
            else:
                # Official catalogue does not provide manufacturer (NULL) - label as missing
                field_results["manufacturer"] = FieldMatchResult(field="manufacturer", input_value=mfg_input, catalog_value=None, status="missing")
        else:
            field_results["manufacturer"] = FieldMatchResult(field="manufacturer", input_value=None, catalog_value=cat_mfg, status="missing")

        # Price check (MRP / Ceiling Price)
        price_check = {}
        if mrp_input is not None and primary_variant:
            ceiling = float(primary_variant.ceiling_price) if primary_variant.ceiling_price is not None else None
            variant_mrp = float(primary_variant.mrp) if primary_variant.mrp is not None else None

            price_check["input_mrp"] = float(mrp_input)
            price_check["catalog_ceiling_price"] = ceiling
            price_check["catalog_mrp"] = variant_mrp

            if ceiling and float(mrp_input) > ceiling * 1.05:
                price_check["status"] = "ceiling_violation"
                field_results["mrp"] = FieldMatchResult(
                    field="mrp",
                    input_value=f"₹{mrp_input:.2f}",
                    catalog_value=f"₹{ceiling:.2f} (Ceiling)",
                    status="mismatch",
                )
                mismatched_fields.append("mrp")
            else:
                price_check["status"] = "within_ceiling" if ceiling else "recorded"
                field_results["mrp"] = FieldMatchResult(
                    field="mrp",
                    input_value=f"₹{mrp_input:.2f}",
                    catalog_value=f"₹{ceiling or variant_mrp:.2f}" if (ceiling or variant_mrp) else None,
                    status="match",
                )
        layer2.price_check = price_check

        layer2.field_results = field_results
        layer2.mismatched_fields = mismatched_fields
        if mismatched_fields:
            layer2.status = "MISMATCH"
        else:
            layer2.status = "MATCH"

    # 4. LAYER 3: Batch Regulatory Alerts Lookup
    layer3 = Layer3Result(layer="Layer 3: Batch Regulatory Alerts")
    confirmed_alerts: List[RegulatoryAlert] = []
    collision_alerts: List[RegulatoryAlert] = []

    # Query distinct notice months for the standardized clearance notice
    months_stmt = (
        select(RegulatoryAlert.notice_month)
        .where(RegulatoryAlert.notice_month.isnot(None), RegulatoryAlert.is_active == True)
        .distinct()
        .order_by(RegulatoryAlert.notice_month)
    )
    imported_months_raw = [r[0] for r in (await session.execute(months_stmt)).all()]
    months_str = ", ".join(imported_months_raw) if imported_months_raw else "All active notices"

    if batch_input:
        layer3.checked = True
        layer3.batch_number = batch_input
        norm_input_batch = re.sub(r"[\s\-_/]+", "", batch_input).lower()

        # Input drug and manufacturer candidate values
        input_drug = (
            brand_input
            or generic_input
            or (primary_medicine.brand_name if primary_medicine else "")
            or (primary_medicine.generic_name if primary_medicine else "")
        )
        input_mfg = (
            mfg_input
            or (primary_variant.manufacturer.name if primary_variant and primary_variant.manufacturer else None)
        )

        # Retrieve active alerts
        all_active_alerts_stmt = select(RegulatoryAlert).where(RegulatoryAlert.is_active == True)
        all_active_alerts = list((await session.execute(all_active_alerts_stmt)).scalars().all())

        # Match on normalized batch number (case/space/hyphen-insensitive)
        for alert in all_active_alerts:
            if not alert.batch_number:
                continue
            norm_alert_batch = re.sub(r"[\s\-_/]+", "", alert.batch_number).lower()
            if norm_alert_batch != norm_input_batch:
                continue

            # Compare drug name
            d_match = False
            if getattr(alert, "medicine_id", None) and primary_medicine and alert.medicine_id == primary_medicine.medicine_id:
                d_match = True
            elif input_drug and alert.drug_name:
                n1 = normalize_text(input_drug).lower()
                n2 = normalize_text(alert.drug_name).lower()
                drug_stopwords = {
                    "tablet", "tablets", "capsule", "capsules", "injection", "syrup", "oral", "drops",
                    "eye", "ear", "nasal", "solution", "suspension", "ointment", "cream", "gel", "lotion",
                    "infusion", "sodium", "potassium", "calcium", "chloride", "hydrochloride", "hcl",
                    "phosphate", "sulphate", "sulfate", "acetate", "maleate", "citrate", "hydrate",
                    "dihydrate", "sterile", "ip", "bp", "usp"
                }
                t1 = set(re.findall(r"[a-z]{3,}", n1)) - drug_stopwords
                t2 = set(re.findall(r"[a-z]{3,}", n2)) - drug_stopwords
                if t1 and t2:
                    substantive_overlap = bool(t1 & t2)
                    core_sim = calculate_string_similarity(" ".join(sorted(t1)), " ".join(sorted(t2)))
                    typo_match = any(
                        calculate_string_similarity(tok1, tok2) >= 0.80
                        for tok1 in t1 for tok2 in t2
                    )
                    if substantive_overlap or typo_match or core_sim >= 0.50:
                        d_match = True
                elif n1 in n2 or n2 in n1:
                    d_match = True
                elif calculate_string_similarity(n1, n2) >= 0.70:
                    d_match = True

            # Compare manufacturer
            m_conflict = False
            if input_mfg and alert.manufacturer:
                m1 = normalize_text(input_mfg).lower()
                m2 = normalize_text(alert.manufacturer).lower()
                if not (m1 in m2 or m2 in m1 or calculate_string_similarity(m1, m2) >= 0.50):
                    mt1 = set(re.findall(r"[a-z]{4,}", m1)) - {"laboratories", "pharma", "pharmaceuticals", "biotech", "limited", "private", "unit"}
                    mt2 = set(re.findall(r"[a-z]{4,}", m2)) - {"laboratories", "pharma", "pharmaceuticals", "biotech", "limited", "private", "unit"}
                    if mt1 and mt2 and not (mt1 & mt2):
                        m_conflict = True

            if d_match and not m_conflict:
                confirmed_alerts.append(alert)
            else:
                collision_alerts.append(alert)

    matched_alerts: List[RegulatoryAlert] = confirmed_alerts or collision_alerts

    if confirmed_alerts:
        layer3.status = "ALERT_FOUND"
        layer3.alerts_count = len(confirmed_alerts)
        layer3.alerts = [
            {
                "internal_ref": a.source_record_id,   # MedSure reference only (not an official notice number)
                "batch_number": a.batch_number,
                "medicine_name": a.drug_name or (primary_medicine.brand_name if primary_medicine else None),
                "manufacturer": a.manufacturer,
                "alert_type": "NSQ alert",             # Labelled by source type, not severity
                "alert_date": str(a.alert_date),
                "reason_for_nsq": a.reason_for_nsq,
                "description": a.description,
                "testing_lab": a.testing_lab,
                "source_url": a.source_url,
                "source_file_name": a.source_file_name,
                "page_number": a.page_number,
                "notice_month": a.notice_month,
            }
            for a in confirmed_alerts
        ]
    elif collision_alerts:
        layer3.status = "NEEDS_VERIFICATION"
        layer3.alerts_count = len(collision_alerts)
        first_col = collision_alerts[0]
        layer3.details = (
            f"Batch '{batch_input}' was flagged in an NSQ alert, but for a different medicine "
            f"({first_col.drug_name}) or manufacturer ({first_col.manufacturer or 'Not stated'}). "
            f"Source: {first_col.source_file_name} p.{first_col.page_number}. Verification required."
        )
        layer3.alerts = [
            {
                "internal_ref": a.source_record_id,   # MedSure reference only (not an official notice number)
                "batch_number": a.batch_number,
                "medicine_name": a.drug_name,
                "manufacturer": a.manufacturer,
                "alert_type": "NSQ alert",             # Labelled by source type, not severity
                "alert_date": str(a.alert_date),
                "reason_for_nsq": a.reason_for_nsq,
                "description": a.description,
                "testing_lab": a.testing_lab,
                "source_url": a.source_url,
                "source_file_name": a.source_file_name,
                "page_number": a.page_number,
                "notice_month": a.notice_month,
            }
            for a in collision_alerts
        ]
    else:
        layer3.status = "CLEAR" if batch_input else "SKIPPED"
        layer3.details = (
            f"No NSQ alert found in the imported notices (months: {months_str}). "
            f"This does not confirm the medicine is genuine or safe."
        ) if batch_input else "No batch number provided for alert lookup."

    # 5. Build Matched Record Item & Evidence Links
    matched_medicines: List[MatchedMedicineItem] = []
    evidence_links: List[Dict[str, str]] = []

    if primary_medicine:
        mfg_name = primary_variant.manufacturer.name if primary_variant and primary_variant.manufacturer else None
        mrp_val = float(primary_variant.mrp) if primary_variant and primary_variant.mrp is not None else None
        ceiling_val = float(primary_variant.ceiling_price) if primary_variant and primary_variant.ceiling_price is not None else None

        active_flags = list(field_results.keys())
        if layer1.status == "MATCH":
            active_flags.append("barcode_exact_match" if barcode_input else "gtin_exact_match")

        item = MatchedMedicineItem(
            medicine_id=primary_medicine.medicine_id,
            brand_name=primary_medicine.brand_name,
            generic_name=primary_medicine.generic_name,
            strength=primary_medicine.strength,
            dosage_form=primary_medicine.dosage_form,
            manufacturer=mfg_name,
            confidence_score=confidence,
            match_flags=active_flags,
            source=primary_medicine.source_name,
            source_record_id=primary_medicine.source_record_id,
            source_url=primary_medicine.source_url,
            verification_status=primary_medicine.verification_status or "unverified_source",
            mrp=mrp_val,
            ceiling_price=ceiling_val,
            pack_size=primary_variant.pack_size if primary_variant else None,
            unit=primary_variant.unit if primary_variant else None,
        )
        matched_medicines.append(item)

        if primary_medicine.source_url:
            evidence_links.append({
                "title": f"Source reference: {primary_medicine.source_name or 'Registry'}",
                "url": primary_medicine.source_url,
            })

    for a in matched_alerts:
        if a.source_url:
            page_ref = f" Page {a.page_number}" if getattr(a, "page_number", None) else ""
            evidence_links.append({
                "title": f"CDSCO NSQ Notice: {getattr(a, 'source_file_name', None) or a.source_record_id}{page_ref}",
                "url": a.source_url,
            })

    # 6. Final Status & Reasons Determination
    reasons: List[str] = []
    final_status: str

    if layer3.status == "ALERT_FOUND":
        final_status = STATUS_ALERT_FOUND
        for a in confirmed_alerts:
            pdf_ref = f" (Source: {a.source_file_name} p.{a.page_number})" if getattr(a, "source_file_name", None) else ""
            reasons.append(
                f"Regulatory alert found for batch {a.batch_number}: {a.reason_for_nsq or a.description} ({a.testing_lab or 'CDSCO Lab'}){pdf_ref}."
            )
    elif layer3.status == "NEEDS_VERIFICATION":
        final_status = STATUS_NEEDS_VERIFY
        for a in collision_alerts:
            pdf_ref = f" (Source: {a.source_file_name} p.{a.page_number})" if getattr(a, "source_file_name", None) else ""
            reasons.append(
                f"Batch '{batch_input}' was flagged in an NSQ alert, but for a different medicine "
                f"({a.drug_name}) or manufacturer ({a.manufacturer or 'Not stated'}){pdf_ref}. Verification required."
            )
    elif primary_medicine:
        if mismatched_fields:
            final_status = STATUS_NEEDS_VERIFY
            reasons.append(f"Mismatched details detected in: {', '.join(mismatched_fields)}.")
        elif confidence is not None and confidence < 0.70:
            final_status = STATUS_NEEDS_VERIFY
            reasons.append(f"Partial match confidence ({int(confidence * 100)}%) below threshold for complete catalogue alignment.")
        else:
            final_status = STATUS_MATCH
            reasons.append("Details match registered MedSure catalogue record.")
        if batch_input and layer3.status == "CLEAR":
            reasons.append(layer3.details)
    else:
        final_status = STATUS_NO_MATCH
        confidence = None
        reasons.append("No matching record found in the MedSure catalogue.")
        if batch_input and layer3.status == "CLEAR":
            reasons.append(layer3.details)

    per_layer_results = PerLayerResults(
        layer_1_identifier=layer1,
        layer_2_details=layer2,
        layer_3_batch_alerts=layer3,
    )

    # Legacy RiskAssessment for backward compatibility
    risk_level = "high" if final_status in (STATUS_ALERT_FOUND, STATUS_NO_MATCH) else ("medium" if final_status == STATUS_NEEDS_VERIFY else "low")
    legacy_rec = final_status

    risk_flags = list(mismatched_fields)
    if matched_alerts:
        risk_flags.append("REGULATORY_ALERT_FOUND")
    if final_status == STATUS_NO_MATCH:
        risk_flags.append("NO_MATCHING_CATALOGUE_RECORD")

    return ScanAnalyzeResponse(
        status=final_status,
        confidence=confidence,
        reasons=reasons,
        matched_record=matched_medicines[0] if matched_medicines else None,
        matched_medicines=matched_medicines,
        per_layer_results=per_layer_results,
        mismatched_fields=mismatched_fields,
        regulatory_alerts=[
            RegulatoryAlertRead(
                alert_id=a.alert_id,
                alert_type=a.alert_type or "nsq_alert",
                batch_number=a.batch_number,
                manufacturer=a.manufacturer,
                alert_date=str(a.alert_date),
                source_url=a.source_url,
                description=a.description,
                is_active=a.is_active,
                medicine_id=a.medicine_id,
                variant_id=a.variant_id,
                source_id=a.source_id,
                created_at=a.created_at,
                imported_at=getattr(a, "imported_at", None),
                internal_ref=a.source_record_id,
                risk_rating=getattr(a, "risk_rating", None),
                drug_name=a.drug_name,
                reason_for_nsq=getattr(a, "reason_for_nsq", None),
                testing_lab=getattr(a, "testing_lab", None),
                mfg_date=getattr(a, "mfg_date", None),
                exp_date=getattr(a, "exp_date", None),
                notice_month=getattr(a, "notice_month", None),
                source_file_name=getattr(a, "source_file_name", None),
                source_file_hash=getattr(a, "source_file_hash", None),
                page_number=getattr(a, "page_number", None),
                s_no_in_pdf=getattr(a, "s_no_in_pdf", None),
                row_index_on_page=getattr(a, "row_index_on_page", None),
                row_number=getattr(a, "row_number", None),
                is_state=getattr(a, "is_state", None),
                licence_note=getattr(a, "licence_note", None),
                source_record_id=a.source_record_id,
            )
            for a in matched_alerts
        ],
        evidence_links=evidence_links,
        disclaimer=DISCLAIMER_TEXT,
        risk_assessment=RiskAssessment(
            overall_risk=risk_level,
            flags=risk_flags,
            recommendation=legacy_rec,
            explanation="; ".join(reasons),
        ),
        recommendation=legacy_rec,
    )


async def verify_medicine_strict(
    session: AsyncSession,
    payload: MedicineVerifyRequest,
) -> MedicineVerifyResponse:
    """Unified strict verification calling analyze_scan_or_query."""
    analysis = await analyze_scan_or_query(session, payload)
    return MedicineVerifyResponse(
        status=analysis.status,
        confidence=analysis.confidence,
        reasons=analysis.reasons,
        medicine=analysis.matched_record,
        matched_medicines=analysis.matched_medicines,
        per_layer_results=analysis.per_layer_results,
        mismatched_fields=analysis.mismatched_fields,
        regulatory_alerts=analysis.regulatory_alerts,
        evidence_links=analysis.evidence_links,
        disclaimer=analysis.disclaimer,
        risk_assessment=analysis.risk_assessment,
    )

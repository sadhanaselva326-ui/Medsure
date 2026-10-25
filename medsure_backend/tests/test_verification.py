import pytest


@pytest.mark.asyncio
async def test_scan_analyze_with_barcode(client):
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "brand_name": "Dolo",
            "strength": "650mg",
            "batch_number": "DL650201",
            "expiry_date": "2027-08",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["matched_medicines"]) >= 1
    matched = data["matched_medicines"][0]
    assert matched["brand_name"] == "Dolo 650"
    assert matched["confidence_score"] == 1.0
    assert "barcode_exact_match" in matched["match_flags"]
    assert data["risk_assessment"]["recommendation"] == "Matches a catalogue record"


@pytest.mark.asyncio
async def test_scan_analyze_with_ocr_text(client):
    payload = {
        "ocr_text": "Dolo 650 Paracetamol IP 650mg Mfg: Micro Labs Batch: DL650201 Exp: 08/2027",
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["matched_medicines"]) >= 1
    assert data["matched_medicines"][0]["brand_name"] == "Dolo 650"
    assert data["risk_assessment"]["recommendation"] == "Matches a catalogue record"


@pytest.mark.asyncio
async def test_scan_analyze_critical_recall_alert(client):
    # Recall exists on batch 'DL650-RECALL-99'
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "brand_name": "Dolo",
            "batch_number": "DL650-RECALL-99",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["regulatory_alerts"]) >= 1
    assert data["risk_assessment"]["overall_risk"] == "high"
    assert data["risk_assessment"]["recommendation"] == "Regulatory alert found"
    assert "REGULATORY_ALERT_FOUND" in data["risk_assessment"]["flags"]


@pytest.mark.asyncio
async def test_medicine_verify_strict(client):
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "brand_name": "Dolo",
            "strength": "650mg",
        },
        "strict_mode": True,
    }
    response = await client.post("/api/medicine/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Matches a catalogue record"
    assert data["confidence"] == 1.0
    assert data["medicine"]["brand_name"] == "Dolo 650"


@pytest.mark.asyncio
async def test_partial_mismatch_wrong_strength(client):
    """Fails match when strength does not match catalogue record."""
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "strength": "1000mg",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Needs verification"
    assert "strength" in data["mismatched_fields"]


@pytest.mark.asyncio
async def test_partial_mismatch_wrong_manufacturer(client):
    """Fails match when manufacturer does not match catalogue record."""
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "manufacturer": "Pfizer Healthcare India",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Needs verification"
    assert "manufacturer" in data["mismatched_fields"]


@pytest.mark.asyncio
async def test_same_product_different_batch(client):
    """Product matches catalogue and non-alert batch is verified CLEAR."""
    payload = {
        "barcode": "8901234001011",
        "extracted_fields": {
            "batch_number": "BATCH-OK-9921",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Matches a catalogue record"
    assert len(data["regulatory_alerts"]) == 0
    assert data["per_layer_results"]["layer_3_batch_alerts"]["status"] == "CLEAR"


@pytest.mark.asyncio
async def test_empty_input(client):
    """Empty payload returns Insufficient input label."""
    payload = {
        "extracted_fields": {},
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Insufficient input"
    assert data["confidence"] is None
    assert "Insufficient input" in data["reasons"][0]


@pytest.mark.asyncio
async def test_malformed_barcode(client):
    """Malformed non-numeric barcode does not crash engine and handles gracefully."""
    payload = {
        "barcode": "!@#INVALID_BARCODE_$%^&*",
        "extracted_fields": {},
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("No matching record in the MedSure catalogue", "Insufficient input")


@pytest.mark.asyncio
async def test_response_with_no_confidence_value(client):
    """When no catalogue match is found, confidence is null (None), not fabricated to 0.85."""
    payload = {
        "extracted_fields": {
            "brand_name": "NonExistentMedicine999Z",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "No matching record in the MedSure catalogue"
    assert data["confidence"] is None


@pytest.mark.asyncio
async def test_matching_case_a_alert_match(client):
    """Case A: Batch + Drug match returns 'Regulatory alert found'."""
    payload = {
        "extracted_fields": {
            "brand_name": "Dolo 650",
            "batch_number": "DL650-RECALL-99",
            "manufacturer": "Micro Labs Ltd",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Regulatory alert found"
    assert data["per_layer_results"]["layer_3_batch_alerts"]["status"] == "ALERT_FOUND"
    assert len(data["regulatory_alerts"]) >= 1


@pytest.mark.asyncio
async def test_matching_case_b_clean_batch(client):
    """Case B: Same drug with clean batch returns CLEAR with disclaimer."""
    payload = {
        "extracted_fields": {
            "brand_name": "Dolo 650",
            "batch_number": "DL650-CLEAN-01",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["per_layer_results"]["layer_3_batch_alerts"]["status"] == "CLEAR"
    assert "No NSQ alert found in the imported notices" in data["per_layer_results"]["layer_3_batch_alerts"]["details"]
    assert "does not confirm" in data["per_layer_results"]["layer_3_batch_alerts"]["details"]


@pytest.mark.asyncio
async def test_matching_case_c_batch_collision_needs_verification(client):
    """Case C: Batch matches but drug is different returns 'Needs verification'."""
    payload = {
        "extracted_fields": {
            "brand_name": "Amoxicillin 500mg",
            "batch_number": "DL650-RECALL-99",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Needs verification"
    assert data["per_layer_results"]["layer_3_batch_alerts"]["status"] == "NEEDS_VERIFICATION"
    assert "was flagged in an NSQ alert, but for a different medicine" in data["per_layer_results"]["layer_3_batch_alerts"]["details"]


@pytest.mark.asyncio
async def test_unrelated_drug_with_alert_batch_no_catalogue_match(client):
    """
    Regression: brand_name='Carboxymethyl Cellulose Sodium Eye Drops IP', batch='MO24H27'.
    When no high-confidence match exists the response must NOT show a catalogue medicine.
    matched_record must be null, status must be 'No matching record in the MedSure catalogue'
    (or 'Needs verification' if batch collision), and no matched_medicines entry may carry
    an unrelated drug name.
    """
    payload = {
        "extracted_fields": {
            "brand_name": "Carboxymethyl Cellulose Sodium Eye Drops IP",
            "batch_number": "MO24H27",
        }
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # matched_record must be null – we must NOT surface an unrelated catalogue item
    assert data["matched_record"] is None, (
        f"Expected matched_record=null for unrelated drug, got: {data.get('matched_record')}"
    )

    # No matched_medicines entry should carry a completely unrelated drug name (e.g. Thyroxine)
    for m in data.get("matched_medicines", []):
        name = (m.get("brand_name") or "").lower()
        assert "thyroxine" not in name, (
            f"False positive catalogue match '{m['brand_name']}' for Carboxymethyl Cellulose query"
        )

    # Status must be no-match or needs-verification (not "Matches a catalogue record")
    assert data["status"] in (
        "No matching record in the MedSure catalogue",
        "Needs verification",
    ), f"Unexpected status '{data['status']}' for unrelated drug query"

    # confidence must be null when no catalogue match is found
    if data["matched_record"] is None:
        assert data["confidence"] is None, (
            f"confidence must be null when matched_record is null, got {data['confidence']}"
        )


@pytest.mark.asyncio
async def test_batch_only_no_catalogue_medicine_exposed(client):
    """
    Batch-only lookup (no drug name). matched_record and matched_medicines must be empty/null.
    """
    payload = {
        "extracted_fields": {
            "batch_number": "MO24H27",
        }
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # No catalogue medicine should be surfaced from a batch-only lookup
    assert data["matched_record"] is None, (
        f"Batch-only lookup must not surface a catalogue medicine: {data.get('matched_record')}"
    )
    assert data.get("matched_medicines", []) == [], (
        f"Batch-only lookup must not surface matched_medicines: {data.get('matched_medicines')}"
    )
    # confidence must be null
    assert data["confidence"] is None


@pytest.mark.asyncio
async def test_alert_dict_uses_internal_ref_not_alert_code(client):
    """
    When an alert is returned, the dict must have key 'internal_ref' (not 'alert_code')
    and 'alert_type' (not 'severity').
    """
    payload = {
        "extracted_fields": {
            "brand_name": "Dolo 650",
            "batch_number": "DL650-RECALL-99",
            "manufacturer": "Micro Labs Ltd",
        },
    }
    response = await client.post("/api/scan/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    layer3_alerts = data.get("per_layer_results", {}).get("layer_3_batch_alerts", {}).get("alerts", [])
    assert layer3_alerts, "Expected at least one alert in layer_3_batch_alerts.alerts"

    for alert_dict in layer3_alerts:
        assert "internal_ref" in alert_dict, (
            f"Alert dict missing 'internal_ref'; keys found: {list(alert_dict.keys())}"
        )
        assert "alert_code" not in alert_dict, (
            f"Alert dict must NOT contain deprecated 'alert_code' key"
        )
        assert "alert_type" in alert_dict, (
            f"Alert dict missing 'alert_type'; keys found: {list(alert_dict.keys())}"
        )
        assert alert_dict["alert_type"] == "NSQ alert", (
            f"Expected alert_type='NSQ alert', got '{alert_dict.get('alert_type')}'"
        )


def test_banned_label_batch_expiry_consistency():
    """'Batch & Expiry Consistency' must not appear in en.json – it implies batch verification."""
    import os
    frontend_src = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "medsure_frontend", "src")
    )
    en_json_path = os.path.join(frontend_src, "i18n", "en.json")
    with open(en_json_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Batch & Expiry Consistency" not in content, (
        "Banned wording 'Batch & Expiry Consistency' still present in en.json – implies batch verification"
    )


def test_banned_wording_in_frontend():
    """Fails if banned words appear in frontend src or locale files, except values read from /api/health."""
    import os
    import re

    banned_words = ["authentic", "consistent", "fake", "counterfeit", "247,000", "PostgreSQL"]
    frontend_src = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "medsure_frontend", "src")
    )
    violations = []

    for root, _, files in os.walk(frontend_src):
        for f in files:
            if not f.endswith((".js", ".jsx", ".json", ".html", ".css")):
                continue
            fpath = os.path.join(root, f)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()

            for word in banned_words:
                matches = re.findall(rf"\b{re.escape(word)}\b", content, re.IGNORECASE)
                if matches:
                    violations.append(f"{f}: prohibited '{word}' ({len(matches)})")

            content_no_disclaimer = content.replace("does not confirm that a medicine is genuine or safe", "")
            if re.search(r"\bgenuine\b", content_no_disclaimer, re.IGNORECASE):
                violations.append(f"{f}: unapproved 'genuine'")

    assert not violations, f"Banned wording violations detected in frontend: {violations}"

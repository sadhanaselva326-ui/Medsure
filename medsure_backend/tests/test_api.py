import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MedSure Vision"
    assert data["status"] == "online"
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data


@pytest.mark.asyncio
async def test_manufacturers_api(client):
    search_resp = await client.get("/api/manufacturers/search?q=Micro")
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert len(data["data"]) >= 1
    mfg = data["data"][0]
    assert "Micro Labs" in mfg["name"]

    # Detail view
    mfg_id = mfg["manufacturer_id"]
    detail_resp = await client.get(f"/api/manufacturers/{mfg_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["name"] == mfg["name"]
    assert len(detail["medicines"]) >= 1


@pytest.mark.asyncio
async def test_regulatory_alerts_api(client):
    # ?severity= query filter is still supported at DB level; just verify we get results
    list_resp = await client.get("/api/alerts?is_active=true")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data["data"]) >= 1
    first = data["data"][0]
    # severity field must NOT appear in the response schema (removed per Phase 3A.1)
    assert "severity" not in first, (
        f"'severity' must not appear in alert read response; keys: {list(first.keys())}"
    )
    # internal_ref must be present (replaces deprecated alert_code)
    assert "internal_ref" in first, f"'internal_ref' missing from alert; keys: {list(first.keys())}"
    # alert_type must be present
    assert "alert_type" in first, f"'alert_type' missing from alert; keys: {list(first.keys())}"

    # Batch alert check
    batch_resp = await client.get("/api/alerts/batch/DL650-RECALL-99")
    assert batch_resp.status_code == 200
    alerts = batch_resp.json()
    assert len(alerts) >= 1
    assert alerts[0]["batch_number"] == "DL650-RECALL-99"

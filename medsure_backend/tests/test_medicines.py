import pytest
import uuid


@pytest.mark.asyncio
async def test_search_medicines(client):
    response = await client.get("/api/medicines/search?q=Dolo")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1
    first = data["data"][0]
    assert "Dolo" in first["brand_name"]
    assert first["manufacturer"] == "Micro Labs Ltd"
    assert first["mrp"] == 34.50


@pytest.mark.asyncio
async def test_search_with_filters(client):
    response = await client.get("/api/medicines/search?dosage_form=Tablet&prescription_status=otc")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 2
    for item in data["data"]:
        assert item["dosage_form"].lower() == "tablet"


@pytest.mark.asyncio
async def test_get_medicine_by_gtin(client):
    response = await client.get("/api/medicines/by-code/8901234001011")
    assert response.status_code == 200
    med = response.json()
    assert med["brand_name"] == "Dolo 650"
    assert len(med["variants"]) >= 1
    assert med["variants"][0]["mrp"] == 34.50


@pytest.mark.asyncio
async def test_get_medicine_by_id_and_substitutes(client):
    # First search to get ID
    search_resp = await client.get("/api/medicines/search?q=Dolo")
    med_id = search_resp.json()["data"][0]["medicine_id"]

    # Get details
    detail_resp = await client.get(f"/api/medicines/{med_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["medicine_id"] == med_id
    assert detail["brand_name"] == "Dolo 650"
    assert "substitutes" in detail

    # Get substitutes directly
    subs_resp = await client.get(f"/api/medicines/{med_id}/substitutes")
    assert subs_resp.status_code == 200
    subs = subs_resp.json()
    assert len(subs) >= 1
    assert subs[0]["brand_name"] == "Crocin Advance"
    assert subs[0]["similarity_score"] == 0.92


@pytest.mark.asyncio
async def test_get_medicine_not_found(client):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/medicines/{fake_id}")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_404"

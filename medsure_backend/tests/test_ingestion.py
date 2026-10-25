import pytest


@pytest.mark.asyncio
async def test_create_and_list_sources(client):
    source_payload = {
        "source_name": "eka_care_api",
        "source_type": "aggregator",
        "source_url": "https://developer.eka.care",
        "verification_status": "verified",
    }
    create_resp = await client.post("/api/admin/sources", json=source_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["source_name"] == "eka_care_api"
    assert "source_id" in created

    # List sources
    list_resp = await client.get("/api/admin/sources")
    assert list_resp.status_code == 200
    sources = list_resp.json()
    names = [s["source_name"] for s in sources]
    assert "eka_care_api" in names
    assert "abdm_cdci" in names


@pytest.mark.asyncio
async def test_bulk_ingestion(client):
    # Fetch source ID
    sources_resp = await client.get("/api/admin/sources")
    source_id = sources_resp.json()[0]["source_id"]

    ingest_payload = {
        "source_id": source_id,
        "format": "json",
        "raw_data": [
            {
                "brand_name": "Calpol 500",
                "generic_name": "Paracetamol 500mg",
                "manufacturer": "GSK",
                "dosage_form": "Tablet",
                "strength": "500 mg",
                "price": 20.00,
                "pack_size": 15,
                "barcode": "8901234777015",
            },
            {
                "brand_name": "Lipitor 10",
                "generic_name": "Atorvastatin 10mg",
                "manufacturer": "Pfizer",
                "dosage_form": "Tablet",
                "strength": "10 mg",
                "price": 85.00,
                "pack_size": 10,
                "barcode": "8901234777010",
            },
        ],
    }
    ingest_resp = await client.post("/api/admin/ingest", json=ingest_payload)
    assert ingest_resp.status_code == 200
    stats = ingest_resp.json()
    assert stats["imported"] == 2
    assert stats["failed"] == 0

    # Verify search finds the new medicine
    search_resp = await client.get("/api/medicines/search?q=Calpol")
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_admin_system_stats(client):
    stats_resp = await client.get("/api/admin/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_medicines"] >= 2
    assert stats["total_manufacturers"] >= 1
    assert "coverage_by_source" in stats

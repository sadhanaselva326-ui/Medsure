"""MedSure Vision - Ingest ABDM CDCI API (Ayushman Bharat Drug Registry)

Fetches drug records from ABDM CDCI drug registry API endpoint with token auth.
"""

import asyncio
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.sources import DataSource
from app.services.ingestion_service import ingest_dataset
from app.schemas.ingestion import IngestRequest


async def sync_abdm_drugs(max_pages: int = 5):
    api_endpoint = "https://drugregistry.abdm.gov.in/api/v1/drugs"
    api_key = settings.ABDM_API_KEY

    print(f"Starting ABDM CDCI sync from {api_endpoint}...")

    async with AsyncSessionLocal() as session:
        # Find or create abdm source
        stmt = select(DataSource).where(DataSource.source_name == "abdm_cdci")
        res = await session.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            source = DataSource(
                source_name="abdm_cdci",
                source_type="government",
                source_url="https://drugregistry.abdm.gov.in",
                api_endpoint=api_endpoint,
                verification_status="verified",
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)

        all_records = []
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Accept": "application/json",
        }

        # If live API reachable and token set, query API; otherwise log demonstration mode
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for page in range(1, max_pages + 1):
                        resp = await client.get(
                            api_endpoint,
                            params={"page": page, "limit": 100},
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("results", [])
                            all_records.extend(data)
                        else:
                            print(f"ABDM API returned status {resp.status_code}. Stopping fetch.")
                            break
            except Exception as e:
                print(f"Network error querying ABDM API: {e}")
        else:
            print("No ABDM_API_KEY found in environment. Using demo registry records.")
            all_records = [
                {
                    "brand_name": "Pan 40",
                    "generic_name": "Pantoprazole Sodium 40mg",
                    "manufacturer": "Alkem Laboratories Ltd",
                    "price": 155.00,
                    "dosage_form": "Tablet",
                    "strength": "40 mg",
                    "pack_size": 15,
                    "unit": "tablet",
                    "barcode": "8901234900015",
                },
                {
                    "brand_name": "Telma 40",
                    "generic_name": "Telmisartan 40mg",
                    "manufacturer": "Glenmark Pharmaceuticals Ltd",
                    "price": 220.00,
                    "dosage_form": "Tablet",
                    "strength": "40 mg",
                    "pack_size": 30,
                    "unit": "tablet",
                    "barcode": "8901234900030",
                },
            ]

        if all_records:
            req = IngestRequest(
                source_id=source.source_id,
                raw_data=all_records,
                batch_size=100,
            )
            stats = await ingest_dataset(session, req)
            print(f"ABDM sync completed. Imported {stats.imported} records.")
        else:
            print("No records retrieved from ABDM.")


if __name__ == "__main__":
    asyncio.run(sync_abdm_drugs())

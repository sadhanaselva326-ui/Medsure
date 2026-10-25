"""MedSure Vision - Database Seeding Script (DEPRECATED FOR DEMO BENCHMARKS)

Demo benchmark records have been permanently removed from MedSure Vision.
This script now executes the official source ingestion pipeline (PMBI, NPPA, CDSCO)
to ensure only real, source-backed medicines populate the catalogue.
"""

import asyncio
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine, Base
from scripts.data_ingestion.pipeline import DataIngestionPipeline
from scripts.data_ingestion.adapters import (
    PMBIJanAushadhiAdapter,
    NPPACeilingPriceAdapter,
    CDSCOAlertAdapter,
)


async def seed():
    print("=" * 65)
    print("NOTICE: Demo benchmark seeding has been disabled.")
    print("Executing official source-backed ingestion pipeline...")
    print("=" * 65)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    pipeline = DataIngestionPipeline()
    adapters = [
        PMBIJanAushadhiAdapter(),
        NPPACeilingPriceAdapter(),
        CDSCOAlertAdapter(),
    ]

    async with AsyncSessionLocal() as session:
        for adapter in adapters:
            print(f">> Ingesting official source: {adapter.source_name}...")
            stats = await pipeline.run_adapter(session, adapter)
            print(f"   Status: {stats.status}, Imported: {stats.records_imported}, Skipped: {stats.records_skipped}")

    print("\nOfficial source ingestion complete. Catalogue contains ONLY real source-backed data.")


if __name__ == "__main__":
    asyncio.run(seed())

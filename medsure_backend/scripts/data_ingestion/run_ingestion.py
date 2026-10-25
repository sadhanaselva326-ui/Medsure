"""run_ingestion.py - Command-line interface for running official source ingestion.

Usage:
    python scripts/data_ingestion/run_ingestion.py --source all
    python scripts/data_ingestion/run_ingestion.py --source pmbi
    python scripts/data_ingestion/run_ingestion.py --source nppa
    python scripts/data_ingestion/run_ingestion.py --source cdsco
"""

import argparse
import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import AsyncSessionLocal, engine, Base
from scripts.data_ingestion import (
    DataIngestionPipeline,
    PMBIJanAushadhiAdapter,
    NPPACeilingPriceAdapter,
    CDSCOAlertAdapter,
)
from scripts.data_ingestion.adapters.cdsco_adapter import _is_fixture_path


async def main():
    parser = argparse.ArgumentParser(description="MedSure Vision Official Source Ingestion Pipeline")
    parser.add_argument(
        "--source",
        choices=["all", "pmbi", "nppa", "cdsco"],
        default="all",
        help="Which official data source adapter to run (default: all)",
    )
    parser.add_argument("--pmbi-file", type=str, default="", help="Optional custom PMBI catalogue file path")
    parser.add_argument("--nppa-file", type=str, default="", help="Optional custom NPPA ceiling price file path")
    parser.add_argument("--cdsco-file", type=str, default="", help="Optional custom CDSCO alert file path")
    args = parser.parse_args()

    # Fixture-isolation guard: refuse test fixture paths at CLI level
    if args.cdsco_file and _is_fixture_path(args.cdsco_file):
        print(
            f"[ERROR] --cdsco-file points to a test/fixture path: {args.cdsco_file!r}\n"
            "        Fixture files must never be loaded into the production database.\n"
            "        Place real CDSCO downloads in scripts/data_ingestion/downloads/cdsco/"
        )
        sys.exit(1)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    pipeline = DataIngestionPipeline()
    adapters = []

    if args.source in ("all", "pmbi"):
        adapters.append(PMBIJanAushadhiAdapter(args.pmbi_file if args.pmbi_file else None))
    if args.source in ("all", "nppa"):
        adapters.append(NPPACeilingPriceAdapter(args.nppa_file if args.nppa_file else None))
    if args.source in ("all", "cdsco"):
        adapters.append(CDSCOAlertAdapter(args.cdsco_file if args.cdsco_file else None))

    print("=" * 65)
    print("MEDSURE VISION - OFFICIAL DATA SOURCE INGESTION PIPELINE")
    print("=" * 65)

    total_imported = 0
    total_updated = 0
    total_skipped = 0
    total_errors = 0

    async with AsyncSessionLocal() as session:
        for adapter in adapters:
            print(f"\n>> Running adapter: {adapter.__class__.__name__} [{adapter.source_name}]")
            print(f"   Source URL: {adapter.source_url}")
            try:
                stats = await pipeline.run_adapter(session, adapter)
                print(f"   Status: {stats.status.upper()}")
                print(f"   Records Read:     {stats.records_read}")
                print(f"   Records Imported: {stats.records_imported}")
                print(f"   Records Updated:  {stats.records_updated}")
                print(f"   Records Skipped:  {stats.records_skipped}")
                print(f"   Errors:           {stats.errors_count}")
                if stats.error_summary:
                    for err in stats.error_summary[:3]:
                        print(f"     ! Error detail: {err}")

                total_imported += stats.records_imported
                total_updated += stats.records_updated
                total_skipped += stats.records_skipped
                total_errors += stats.errors_count

            except Exception as e:
                print(f"   [!] Adapter failed: {e}")
                total_errors += 1

    print("\n" + "=" * 65)
    print("INGESTION RUN SUMMARY")
    print(f"  Total Imported: {total_imported}")
    print(f"  Total Updated:  {total_updated}")
    print(f"  Total Skipped:  {total_skipped}")
    print(f"  Total Errors:   {total_errors}")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())

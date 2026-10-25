"""cdsco_adapter.py - Official CDSCO NSQ & Drug Alert Data Adapter.

Imports verified Not of Standard Quality (NSQ) drug alerts, batch recalls, and
regulatory notices issued by the Central Drugs Standard Control Organisation (CDSCO),
Ministry of Health and Family Welfare, Government of India.

IMPORTANT - fixture isolation policy
=====================================
This adapter MUST NOT load data from the tests/ directory or from any file whose
name contains 'fixture'.  Those files are synthetic test data and must never enter
the production database.

Real CDSCO downloads belong in:
  scripts/data_ingestion/downloads/cdsco/
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

from scripts.data_ingestion.base import BaseSourceImporter, RawMedicineRecord, RawRegulatoryAlert
from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_manufacturer,
)


def _is_fixture_path(path: str) -> bool:
    """Return True if *path* points into the tests/ directory or looks like a fixture file."""
    resolved = Path(path).resolve()
    parts = [p.lower() for p in resolved.parts]
    # Reject paths that pass through a 'tests' directory component
    if "tests" in parts:
        return True
    # Reject filenames that are clearly fixture files
    stem = resolved.stem.lower()
    if "fixture" in stem:
        return True
    return False


class CDSCOAlertAdapter(BaseSourceImporter):
    """Adapter for official CDSCO monthly NSQ (Not of Standard Quality) drug alerts.

    Only reads files from scripts/data_ingestion/downloads/ (or an explicitly
    supplied path outside tests/).  Raises ValueError if a fixture path is supplied.
    """

    def __init__(self, data_file_path: Optional[str] = None):
        if data_file_path:
            if _is_fixture_path(data_file_path):
                raise ValueError(
                    f"CDSCOAlertAdapter refuses to load from a test/fixture path: {data_file_path!r}. "
                    "Place real CDSCO downloads in scripts/data_ingestion/downloads/cdsco/ and "
                    "use test fixtures only via conftest.py or the tests/fixtures/ directory."
                )
            if os.path.exists(data_file_path):
                self.file_path = data_file_path
            else:
                raise FileNotFoundError(
                    f"CDSCOAlertAdapter: supplied file not found: {data_file_path!r}"
                )
        else:
            # Default: look in the downloads directory only (never in data/ or tests/)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.file_path = os.path.join(base_dir, "downloads", "cdsco", "cdsco_nsq_alerts.json")

    @property
    def source_name(self) -> str:
        return "cdsco_nsq"

    @property
    def source_type(self) -> str:
        return "government"

    @property
    def source_url(self) -> str:
        return "https://cdsco.gov.in"

    async def load_records(self) -> List[RawMedicineRecord]:
        """Alerts are primarily loaded via load_alert_records()."""
        return []

    async def load_alert_records(self) -> List[RawRegulatoryAlert]:
        """Loads and normalizes official CDSCO NSQ alerts from monthly laboratory test lists."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"CDSCO alert file not found at: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        alerts: List[RawRegulatoryAlert] = []
        for item in raw_data:
            dt = date.today()
            if item.get("alert_date"):
                try:
                    dt = datetime.strptime(item["alert_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass

            alert_obj = RawRegulatoryAlert(
                medicine_brand=normalize_brand_name(item.get("medicine_name")),
                generic_name=normalize_generic_name(item.get("generic_name")),
                batch_number=str(item.get("batch_number", "")).strip(),
                manufacturer_name=normalize_manufacturer(item.get("manufacturer")),
                alert_date=dt,
                alert_type="nsq_alert",
                severity=item.get("severity", "high"),
                description=item.get("description", "Not of Standard Quality (NSQ) report issued by CDSCO testing laboratory."),
                reason_for_nsq=item.get("reason_for_nsq"),
                testing_lab=item.get("testing_lab"),
                source_url=self.source_url,
                source_record_id=item.get("alert_code"),
                is_demo=False,
                is_fixture=True,
            )
            alerts.append(alert_obj)

        return alerts

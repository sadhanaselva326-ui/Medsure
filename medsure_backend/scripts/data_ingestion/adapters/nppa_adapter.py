"""nppa_adapter.py - Official NPPA DPCO Ceiling Price Data Adapter.

Imports gazette-notified ceiling prices under the Drugs (Prices Control) Order
(DPCO 2013 / NLEM 2022) issued by the National Pharmaceutical Pricing Authority
(NPPA), Ministry of Chemicals & Fertilizers, Government of India.
"""

import json
import os
from datetime import datetime
from typing import List, Optional

from scripts.data_ingestion.base import BaseSourceImporter, RawMedicineRecord, ProvenanceMeta
from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_strength,
    normalize_dosage_form,
    normalize_pack_size,
    normalize_mrp,
)


class NPPACeilingPriceAdapter(BaseSourceImporter):
    """Adapter for official NPPA DPCO scheduled formulation ceiling prices."""

    def __init__(self, data_file_path: Optional[str] = None):
        if data_file_path and os.path.exists(data_file_path):
            self.file_path = data_file_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.file_path = os.path.join(base_dir, "data", "nppa_dpco_ceiling_prices.json")

    @property
    def source_name(self) -> str:
        return "nppa_ipdms"

    @property
    def source_type(self) -> str:
        return "government"

    @property
    def source_url(self) -> str:
        return "https://nppaindia.nic.in"

    async def load_records(self) -> List[RawMedicineRecord]:
        """Loads and normalizes official NPPA scheduled formulations and ceiling prices."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"NPPA data file not found at: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        records: List[RawMedicineRecord] = []
        for item in raw_data:
            generic_norm = normalize_generic_name(item.get("generic_name") or item.get("formulation_name"))
            strength_norm = normalize_strength(item.get("strength"))
            dosage_norm = normalize_dosage_form(item.get("dosage_form"))

            brand_norm = f"NPPA Ceiling {generic_norm}"
            if strength_norm:
                brand_norm += f" {strength_norm}"

            unit_ceiling = normalize_mrp(item.get("ceiling_price"))
            pack_size, unit = normalize_pack_size(10, item.get("unit"))
            total_ceiling = round(unit_ceiling * pack_size, 2) if unit_ceiling else None

            nppa_code = item.get("nppa_code")
            notif_no = item.get("notification_number", "DPCO 2013")

            provenance = ProvenanceMeta(
                source_name=self.source_name,
                source_url=self.source_url,
                source_record_id=nppa_code,
                is_demo=False,
            )

            rec = RawMedicineRecord(
                brand_name=brand_norm,
                generic_name=generic_norm,
                strength=strength_norm,
                dosage_form=dosage_norm,
                composition={
                    "active_ingredients": [{"name": generic_norm, "strength": strength_norm}],
                    "excipients": [],
                },
                therapeutic_category=["DPCO Scheduled Formulation", "Essential Medicine"],
                prescription_status="prescription",
                confidence_score=0.99,
                manufacturer_name=None,
                manufacturer_address=None,
                pack_size=pack_size,
                unit=unit,
                packaging_description=f"DPCO Standard Pack ({pack_size} {unit}s) - {notif_no}",
                mrp=total_ceiling,
                ceiling_price=total_ceiling,
                gtin=None,  # Do not invent barcodes where not published
                barcode=None,
                identifier_type="nppa_formulation_code",
                identifier_value=nppa_code,
                provenance=provenance,
            )
            records.append(rec)

        return records

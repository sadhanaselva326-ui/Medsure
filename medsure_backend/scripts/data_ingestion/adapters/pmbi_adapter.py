"""pmbi_adapter.py - Official PMBI (Jan Aushadhi) Product & MRP Data Adapter.

Imports verified generic formulation products and public MRP rates published
by the Pharmaceuticals & Medical Devices Bureau of India (PMBI), Ministry of
Chemicals & Fertilizers, Government of India.
"""

import json
import os
from typing import List, Optional

from scripts.data_ingestion.base import BaseSourceImporter, RawMedicineRecord, ProvenanceMeta
from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_strength,
    normalize_dosage_form,
    normalize_manufacturer,
    normalize_pack_size,
    normalize_mrp,
    normalize_therapeutic_category,
)


class PMBIJanAushadhiAdapter(BaseSourceImporter):
    """Adapter for official PMBI / PMBJP Jan Aushadhi product catalogue."""

    def __init__(self, data_file_path: Optional[str] = None):
        if data_file_path and os.path.exists(data_file_path):
            self.file_path = data_file_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.file_path = os.path.join(base_dir, "data", "pmbi_janaushadhi_catalogue.json")

    @property
    def source_name(self) -> str:
        return "pmbi_janaushadhi"

    @property
    def source_type(self) -> str:
        return "government"

    @property
    def source_url(self) -> str:
        return "https://janaushadhi.gov.in"

    async def load_records(self) -> List[RawMedicineRecord]:
        """Loads and normalizes PMBI product records from official catalogue."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"PMBI data file not found at: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        records: List[RawMedicineRecord] = []
        for item in raw_data:
            generic_norm = normalize_generic_name(item.get("generic_name"))
            strength_norm = normalize_strength(item.get("strength"))
            dosage_norm = normalize_dosage_form(item.get("dosage_form"))

            # Jan Aushadhi brand convention
            brand_norm = f"Jan Aushadhi {generic_norm}"
            if strength_norm:
                brand_norm += f" {strength_norm}"

            pack_size, unit = normalize_pack_size(item.get("pack_size"), item.get("unit"))
            mrp_val = normalize_mrp(item.get("mrp"))
            categories = normalize_therapeutic_category(item.get("therapeutic_category"))

            drug_code = item.get("drug_code")
            provenance = ProvenanceMeta(
                source_name=self.source_name,
                source_url=self.source_url,
                source_record_id=drug_code,
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
                therapeutic_category=categories,
                prescription_status=item.get("prescription_status", "prescription"),
                confidence_score=0.98,
                manufacturer_name=None,
                manufacturer_address=None,
                pack_size=pack_size,
                unit=unit,
                packaging_description=f"Pack of {pack_size} {unit}s",
                mrp=mrp_val,
                ceiling_price=None,
                gtin=None,  # Do not invent barcodes where not published
                barcode=None,
                identifier_type="pmbi_item_code",
                identifier_value=drug_code,
                provenance=provenance,
            )
            records.append(rec)

        return records

"""deduplicator.py - Medicine and Variant deduplication and provenance merging.

Implements composite hashing and matching across:
brand name + active ingredient + strength + dosage form + manufacturer + pack size.
Preserves existing source provenance rather than destructively overwriting records.
"""

import hashlib
from typing import Optional
from difflib import SequenceMatcher

from scripts.data_ingestion.normalizer import (
    normalize_brand_name,
    normalize_generic_name,
    normalize_strength,
    normalize_dosage_form,
    normalize_manufacturer,
    normalize_pack_size,
)


def compute_medicine_hash(
    brand_name: str,
    generic_name: str,
    strength: Optional[str] = None,
    dosage_form: Optional[str] = None,
) -> str:
    """Generates a deterministic 32-character SHA-256 hex digest for a medicine formulation.

    Key components: normalized brand + normalized generic + normalized strength + normalized dosage form.
    """
    b_norm = normalize_brand_name(brand_name).lower()
    g_norm = normalize_generic_name(generic_name).lower()
    s_norm = (normalize_strength(strength) or "").lower()
    d_norm = normalize_dosage_form(dosage_form).lower()

    composite = f"{b_norm}|{g_norm}|{s_norm}|{d_norm}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()[:32]


def compute_variant_hash(
    medicine_key: str,
    manufacturer_name: Optional[str] = None,
    pack_size: Optional[int] = None,
    unit: Optional[str] = None,
) -> str:
    """Generates a deterministic 32-character SHA-256 hex digest for a packaging variant.

    Key components: medicine key + normalized manufacturer + pack size + unit.
    """
    mfg_norm = normalize_manufacturer(manufacturer_name).lower()
    size_norm, unit_norm = normalize_pack_size(pack_size, unit)

    composite = f"{medicine_key}|{mfg_norm}|{size_norm}|{unit_norm}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()[:32]


def calculate_similarity(a: str, b: str) -> float:
    """Returns ratio similarity between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

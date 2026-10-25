import re
import difflib
from typing import Optional, Tuple


def normalize_text(text: Optional[str]) -> str:
    """Normalize text for consistent comparison (lowercase, stripped, single spaced)."""
    if not text:
        return ""
    # Remove special punctuation, normalize whitespace
    cleaned = re.sub(r"[^\w\s\.-]", " ", text)
    return " ".join(cleaned.lower().split())


def calculate_string_similarity(a: str, b: str) -> float:
    """Calculates SequenceMatcher similarity between two strings (0.0 to 1.0)."""
    if not a or not b:
        return 0.0
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if a_norm == b_norm:
        return 1.0
    return difflib.SequenceMatcher(None, a_norm, b_norm).ratio()


def calculate_gs1_check_digit(digits_without_check: str) -> int:
    """Calculates GS1 standard modulo-10 check digit for barcode / GTIN."""
    digits = [int(d) for d in digits_without_check if d.isdigit()]
    total = 0
    # Process from right to left, alternating weights 3 and 1
    for i, digit in enumerate(reversed(digits)):
        weight = 3 if i % 2 == 0 else 1
        total += digit * weight
    return (10 - (total % 10)) % 10


def validate_gtin_checksum(code: str) -> bool:
    """Validates if a GTIN-8, GTIN-12, GTIN-13 (EAN-13), or GTIN-14 has a valid GS1 check digit."""
    if not code or not code.isdigit():
        return False
    if len(code) not in (8, 12, 13, 14):
        return False
    expected_check = calculate_gs1_check_digit(code[:-1])
    return int(code[-1]) == expected_check


def is_indian_gs1_code(code: str) -> bool:
    """Checks if barcode prefix corresponds to GS1 India (prefix 890)."""
    if not code or not code.isdigit():
        return False
    clean = code.strip()
    # EAN-13 starts with 890
    if len(clean) == 13 and clean.startswith("890"):
        return True
    # GTIN-14 indicator digit + 890
    if len(clean) == 14 and clean[1:4] == "890":
        return True
    return False


def extract_strength_and_unit(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts numeric strength and unit (e.g., '650mg' -> ('650', 'mg'))."""
    if not text:
        return None, None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|%)", text, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2).lower()
    return None, None


def parse_pack_size_label(
    label: Optional[str],
    default_dosage_form: Optional[str] = None,
) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Robustly parses Indian medicine pack size labels (e.g., 'strip of 10 tablets',

    'bottle of 100 ml syrup', '10 capsules', 'inhaler of 200 doses').

    Returns (pack_size, unit, packaging_description).
    If pack size cannot be determined, returns (None, None, raw_label).
    Never invents arbitrary numbers or units.
    """
    if not label or not str(label).strip():
        return None, None, None

    raw_clean = str(label).strip()
    lowered = raw_clean.lower()

    # Unit canonicalization dictionary
    unit_map = {
        "tablets": "tablet",
        "tablet": "tablet",
        "tabs": "tablet",
        "tab": "tablet",
        "capsules": "capsule",
        "capsule": "capsule",
        "caps": "capsule",
        "cap": "capsule",
        "strips": "strip",
        "strip": "strip",
        "bottles": "bottle",
        "bottle": "bottle",
        "ml": "ml",
        "gm": "gm",
        "g": "gm",
        "grams": "gm",
        "vials": "vial",
        "vial": "vial",
        "ampoules": "ampoule",
        "ampoule": "ampoule",
        "amps": "ampoule",
        "inhalers": "inhaler",
        "inhaler": "inhaler",
        "doses": "doses",
        "rotacaps": "rotacaps",
        "rotacap": "rotacaps",
        "sachets": "sachet",
        "sachet": "sachet",
        "tubes": "tube",
        "tube": "tube",
        "drops": "drops",
        "pills": "tablet",
        "lozenges": "tablet",
    }

    # Pattern 1: 'strip of 10 tablets', 'bottle of 100 ml', 'box of 15 capsules'
    p1 = re.search(
        r"(?:strip|box|blister|packet|pack|bottle|tube|vial|jar|carton)\s+of\s+(\d+)\s*([a-zA-Z]+)?",
        lowered,
    )
    if p1:
        qty = int(p1.group(1))
        raw_u = p1.group(2)
        if raw_u and raw_u in unit_map:
            return qty, unit_map[raw_u], raw_clean
        # E.g. 'strip of 10' -> unit is 'strip' or inferred from dosage form
        if "strip" in lowered:
            inferred = "tablet" if default_dosage_form and "tablet" in default_dosage_form.lower() else "tablet"
            return qty, inferred, raw_clean
        if "bottle" in lowered:
            return qty, "bottle", raw_clean
        if "box" in lowered:
            return qty, "tablet", raw_clean

    # Pattern 2: '100 ml in 1 bottle', '10 tablets in 1 strip', '200 doses in 1 inhaler'
    p2 = re.search(
        r"(\d+)\s*(ml|gm|g|doses|tablets?|capsules?|pills?|sachets?|rotacaps?|vials?)\s+in\s+1\s+",
        lowered,
    )
    if p2:
        qty = int(p2.group(1))
        unit = unit_map.get(p2.group(2), p2.group(2))
        return qty, unit, raw_clean

    # Pattern 3: '100 ml', '15 tablets', '20 capsules', '200 doses', '30 gm'
    p3 = re.search(
        r"(\d+)\s*(ml|gm|g|doses|tablets?|capsules?|pills?|rotacaps?|sachets?|vials?|inhalers?|strips?|bottles?|tubes?)",
        lowered,
    )
    if p3:
        qty = int(p3.group(1))
        unit = unit_map.get(p3.group(2), p3.group(2))
        return qty, unit, raw_clean

    # Pattern 4: standalone integer e.g. '10', '15', '30'
    p4 = re.search(r"^(\d+)$", lowered.strip())
    if p4:
        qty = int(p4.group(1))
        unit = "tablet"
        if default_dosage_form:
            norm_df = default_dosage_form.lower()
            if "syrup" in norm_df or "liquid" in norm_df or "suspension" in norm_df:
                unit = "ml"
            elif "capsule" in norm_df:
                unit = "capsule"
            elif "inhaler" in norm_df:
                unit = "doses"
            elif "cream" in norm_df or "ointment" in norm_df or "gel" in norm_df:
                unit = "gm"
        return qty, unit, raw_clean

    # Fallback: could not safely parse number; preserve label as packaging description
    return None, None, raw_clean


def clean_salt_name(text: Optional[str]) -> str:
    """Extracts cleaned generic salt names from strings like 'Paracetamol (650mg)'

    or 'Amoxicillin IP 500mg + Potassium Clavulanate 125mg'.
    """
    if not text:
        return ""
    # Remove parenthetical quantities e.g. '(650mg)' or '(500mg/5ml)'
    s = re.sub(r"\([^)]*\)", "", str(text))
    # Remove pharmacopoeia markers e.g. ' IP', ' BP', ' USP'
    s = re.sub(r"\b(IP|BP|USP)\b", "", s, flags=re.IGNORECASE)
    # Remove standalone strength numbers and units
    s = re.sub(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%)\b", "", s, flags=re.IGNORECASE)
    return normalize_text(s)


def extract_strength_string(
    text: Optional[str],
    fallback_text: Optional[str] = None,
) -> Optional[str]:
    """Extracts formatted strength string (e.g., '650 mg', '500mg + 125mg')."""
    candidates = [text, fallback_text]
    for c in candidates:
        if not c:
            continue
        # Look for multi-strength (e.g., '500mg + 125mg' or '400mg + 325mg')
        multi = re.search(
            r"(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%)\s*(?:\+\s*\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%))+)",
            str(c),
            re.IGNORECASE,
        )
        if multi:
            return multi.group(1).strip()

        # Look for single strength in parentheses e.g. '(650mg)'
        paren = re.search(r"\((\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%))\)", str(c), re.IGNORECASE)
        if paren:
            val, unit = extract_strength_and_unit(paren.group(1))
            if val and unit:
                return f"{val} {unit}"

        # Standard strength pattern
        val, unit = extract_strength_and_unit(str(c))
        if val and unit:
            return f"{val} {unit}"

    return None


def build_medicine_dedup_keys(
    brand_name: str,
    generic_name: str,
    dosage_form: Optional[str],
    strength: Optional[str],
) -> List[str]:
    """Generates normalized lookup keys for deduplicating parent medicine records."""
    norm_brand = normalize_text(brand_name)
    norm_generic = clean_salt_name(generic_name) or normalize_text(generic_name)
    norm_dosage = normalize_text(dosage_form or "tablet")
    # Singularize dosage form
    if norm_dosage.endswith("s") and len(norm_dosage) > 3:
        norm_dosage = norm_dosage[:-1]

    norm_str = normalize_text(strength or "")

    keys = []
    # Key 1: Exact brand + salt + dosage + strength
    if norm_str:
        keys.append(f"{norm_brand}|{norm_generic}|{norm_dosage}|{norm_str}")
        keys.append(f"{norm_brand}|{norm_generic}||{norm_str}")

    # Key 2: Brand + salt + dosage
    keys.append(f"{norm_brand}|{norm_generic}|{norm_dosage}")

    # Key 3: If brand has dosage form suffix (e.g. 'dolo 650 tablet' -> 'dolo 650')
    for suffix in (" tablet", " capsule", " syrup", " suspension", " injection", " inhaler", " gel", " cream", " drops"):
        if norm_brand.endswith(suffix):
            bare_brand = norm_brand[:-len(suffix)].strip()
            if norm_str:
                keys.append(f"{bare_brand}|{norm_generic}|{norm_dosage}|{norm_str}")
            keys.append(f"{bare_brand}|{norm_generic}|{norm_dosage}")
            keys.append(f"{bare_brand}|{norm_generic}")

    # Key 4: Bare brand + salt
    keys.append(f"{norm_brand}|{norm_generic}")

    return keys


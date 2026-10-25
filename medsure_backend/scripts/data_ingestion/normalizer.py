"""normalizer.py - Standardized entity normalization for Indian medicine records.

Normalizes brand names, active ingredients/generics, strengths, dosage forms,
manufacturers, pack sizes, MRP, and therapeutic categories according to Indian
pharma conventions (IP/BP standards, DPCO, PMBI).
"""

import re
from typing import Any, List, Optional, Tuple


# Known salt synonyms and spelling standardizations (IP vs BP vs USAN)
SALT_SYNONYMS = {
    "amoxycillin": "Amoxicillin",
    "amoxicillin trihydrate": "Amoxicillin",
    "clavulanic acid potassium": "Clavulanic Acid",
    "potassium clavulanate": "Clavulanic Acid",
    "paracetamol ip": "Paracetamol",
    "acetaminophen": "Paracetamol",
    "acetylsalicylic acid": "Aspirin",
    "acetyl salicylic acid": "Aspirin",
    "metformin hydrochloride": "Metformin",
    "metformin hcl": "Metformin",
    "atorvastatin calcium": "Atorvastatin",
    "pantoprazole sodium": "Pantoprazole",
    "pantoprazole sodium sesquihydrate": "Pantoprazole",
    "azithromycin dihydrate": "Azithromycin",
    "salbutamol sulphate": "Salbutamol",
    "albuterol": "Salbutamol",
    "montelukast sodium": "Montelukast",
    "fluticasone propionate": "Fluticasone",
    "salmeterol xinafoate": "Salmeterol",
    "cholecalciferol": "Vitamin D3 (Cholecalciferol)",
    "ascorbic acid": "Vitamin C (Ascorbic Acid)",
}

# Dosage form mapping
DOSAGE_FORM_MAP = {
    "tablet": "Tablet",
    "tab": "Tablet",
    "tablets": "Tablet",
    "film coated tablet": "Tablet",
    "dispersible tablet": "Tablet",
    "enteric coated tablet": "Enteric Coated Tablet",
    "chewable tablet": "Chewable Tablet",
    "effervescent tablet": "Effervescent Tablet",
    "capsule": "Capsule",
    "cap": "Capsule",
    "capsules": "Capsule",
    "soft gelatin capsule": "Capsule",
    "hard gelatin capsule": "Capsule",
    "syrup": "Syrup",
    "syr": "Syrup",
    "suspension": "Suspension",
    "susp": "Suspension",
    "oral suspension": "Suspension",
    "injection": "Injection",
    "inj": "Injection",
    "inhaler": "Inhaler",
    "rotacaps": "Inhaler (Rotacaps)",
    "ointment": "Ointment",
    "cream": "Cream",
    "gel": "Gel",
    "drops": "Drops",
    "eye drops": "Eye Drops",
    "ear drops": "Ear Drops",
    "liquid": "Liquid",
    "lotion": "Lotion",
    "powder": "Powder",
}


def normalize_brand_name(raw: Optional[str]) -> str:
    """Normalizes a medicine brand name.

    Removes packaging descriptors while preserving brand identity and strength numbers.
    e.g. "Augmentin 625 Duo Tablet" -> "Augmentin 625"
    e.g. "Dolo 650mg Tablets (15s)" -> "Dolo 650"
    """
    if not raw:
        return ""
    text = str(raw).strip()

    # Remove parenthetical packaging hints: (10s), (Strip of 10), (Pack of 10)
    text = re.sub(r"\(.*?\)", "", text).strip()

    # Remove common packaging suffixes at the end of the brand string
    suffixes = [
        r"\bstrip\s+of\b.*$",
        r"\bpack\s+of\b.*$",
        r"\bduo\s+tablet\b",
        r"\btablets?\b",
        r"\bcapsules?\b",
        r"\bsyrup\b",
        r"\binjection\b",
        r"\bsuspension\b",
        r"\bointment\b",
        r"\bcream\b",
        r"\bgel\b",
        r"\brotacaps?\b",
        r"\binhaler\b",
        r"\bdrops?\b",
    ]
    for pattern in suffixes:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Clean multiple spaces and trailing hyphens/dots
    text = re.sub(r"\s+", " ", text).strip(" .-")

    # Capitalize appropriately (handle Roman numerals like IP, SR, CR, DS, DT, Forte)
    words = text.split()
    capitalized = []
    for w in words:
        upper_candidates = {"ip", "bp", "usp", "sr", "cr", "er", "ds", "dt", "ls", "cv", "forte", "plus"}
        if w.lower() in upper_candidates:
            capitalized.append(w.upper())
        elif w.isdigit() or any(c.isdigit() for c in w):
            capitalized.append(w.upper())
        else:
            capitalized.append(w.capitalize())

    return " ".join(capitalized)


def normalize_generic_name(raw: Optional[str]) -> str:
    """Normalizes active pharmaceutical ingredient (API) generic composition.

    Standardizes salt names, removes pharmacopoeia tokens ('IP', 'BP'),
    and uses ' + ' as the standard combination delimiter.
    e.g. "Amoxycillin (500mg) + Clavulanic Acid (125mg)" -> "Amoxicillin + Clavulanic Acid"
    """
    if not raw:
        return ""
    text = str(raw).strip()

    # Remove IP / BP / USP notations
    text = re.sub(r"\b(IP|BP|USP)\b", "", text, flags=re.IGNORECASE)

    # Split combinations on '+' or '/' or '&'
    parts = re.split(r"\s*[+&/]\s*", text)
    cleaned_parts = []

    for part in parts:
        p = part.strip()
        if not p:
            continue
        # Strip strength in parentheses: e.g. "Amoxycillin (500mg)" -> "Amoxycillin"
        p = re.sub(r"\(.*?\)", "", p).strip()
        # Strip hydrate / form suffixes
        p = re.sub(r"\b(trihydrate|dihydrate|monohydrate|anhydrous|hemihydrate)\b", "", p, flags=re.IGNORECASE).strip()
        # Strip trailing strength: e.g. "Paracetamol 650 mg" -> "Paracetamol"
        p = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|%)\b.*", "", p, flags=re.IGNORECASE).strip()

        # Clean punctuation and extra spaces
        p = re.sub(r"\s+", " ", p).strip(" .-")

        # Check salt synonyms
        key = p.lower()
        if "amoxycillin" in key or "amoxicillin" in key:
            cleaned_parts.append("Amoxicillin")
        elif key in SALT_SYNONYMS:
            cleaned_parts.append(SALT_SYNONYMS[key])
        else:
            # Capitalize words
            cleaned_parts.append(p.title())

    return " + ".join(cleaned_parts) if cleaned_parts else text.title()


def normalize_strength(raw: Optional[str]) -> Optional[str]:
    """Normalizes strength strings to clean standard format.

    e.g. "650mg" -> "650 mg"
    e.g. "500 mg + 125 mg" -> "500 mg + 125 mg"
    e.g. "15mg/5ml" -> "15 mg / 5 ml"
    """
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    # Replace variations of per / slash: e.g. "15mg/5ml" -> "15 mg / 5 ml"
    text = re.sub(r"\s*/\s*", " / ", text)

    # Standardize spacing before unit: e.g. "650mg" -> "650 mg"
    text = re.sub(r"(\d+(\.\d+)?)\s*(mg|mcg|g|ml|iu|IU|l|L|%)\b", r"\1 \3", text)

    # Standardize units
    text = re.sub(r"\bmg\b", "mg", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmcg\b", "mcg", text, flags=re.IGNORECASE)
    text = re.sub(r"\biu\b", "IU", text, flags=re.IGNORECASE)
    text = re.sub(r"\bml\b", "ml", text, flags=re.IGNORECASE)

    # Clean multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def normalize_dosage_form(raw: Optional[str]) -> str:
    """Normalizes dosage form (tablet, capsule, syrup, etc.)."""
    if not raw:
        return "Tablet"
    clean = str(raw).strip().lower()

    # Sort by key length descending so longer composite phrases like "chewable tablet"
    # match before general substrings like "tablet"
    sorted_forms = sorted(DOSAGE_FORM_MAP.items(), key=lambda item: len(item[0]), reverse=True)
    for pattern, std in sorted_forms:
        if pattern in clean:
            return std

    return clean.capitalize()


def normalize_manufacturer(raw: Optional[str]) -> str:
    """Normalizes manufacturer company name.

    Standardizes common Indian pharma abbreviations and title cases.
    """
    if not raw:
        return "Unknown Manufacturer"
    text = str(raw).strip()

    # Standardize common pharma suffixes
    text = re.sub(r"\b(pvt\.?\s*ltd\.?|private\s+limited)\b", "Pvt Ltd", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(ltd\.?|limited)\b", "Ltd", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(pharmaceuticals?|pharma)\b", "Pharmaceuticals", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(laboratories|labs)\b", "Labs", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(industries)\b", "Industries", text, flags=re.IGNORECASE)

    # Standardize known Indian manufacturers
    known_mfgs = {
        "micro labs": "Micro Labs Ltd",
        "glaxo smithkline": "GlaxoSmithKline Pharmaceuticals Ltd (GSK)",
        "gsk": "GlaxoSmithKline Pharmaceuticals Ltd (GSK)",
        "sanofi": "Sanofi India Ltd",
        "cipla": "Cipla Ltd",
        "sun pharma": "Sun Pharmaceutical Industries Ltd",
        "sun pharmaceutical": "Sun Pharmaceutical Industries Ltd",
        "alembic": "Alembic Pharmaceuticals Ltd",
        "torrent": "Torrent Pharmaceuticals Ltd",
        "zydus": "Zydus Healthcare Ltd",
        "usv": "USV Pvt Ltd",
        "bayer": "Bayer Pharmaceuticals Pvt Ltd",
        "abbott": "Abbott India Ltd",
        "glenmark": "Glenmark Pharmaceuticals Ltd",
        "pfizer": "Pfizer Ltd",
        "pmbi": "Pharmaceuticals & Medical Devices Bureau of India (PMBI)",
        "janaushadhi": "Pharmaceuticals & Medical Devices Bureau of India (PMBI)",
    }

    lower_text = text.lower()
    for pattern, canonical in known_mfgs.items():
        if pattern in lower_text:
            return canonical

    # Title case clean string
    words = text.split()
    return " ".join(w if w in {"Ltd", "Pvt", "GSK", "IP", "USV"} else w.capitalize() for w in words)


def normalize_pack_size(raw_pack: Any, raw_unit: Optional[str] = None) -> Tuple[int, str]:
    """Parses and normalizes pack size quantity and pack unit.

    e.g. "strip of 10 tablets" -> (10, "tablet")
    e.g. "bottle of 100 ml Syrup" -> (100, "ml")
    e.g. 15, "tablet" -> (15, "tablet")
    """
    if raw_pack is None:
        return (10, "tablet")

    if isinstance(raw_pack, (int, float)) and int(raw_pack) > 0:
        unit = str(raw_unit).lower().strip() if raw_unit else "tablet"
        unit_clean = "tablet"
        for candidate in ["tablet", "capsule", "strip", "bottle", "vial", "inhaler", "ml", "ampoule", "patch"]:
            if candidate in unit:
                unit_clean = candidate
                break
        return (int(raw_pack), unit_clean)

    text = str(raw_pack).strip().lower()

    # Search for number in string e.g. "strip of 10 tablets" or "100ml" or "10's"
    num_match = re.search(r"(\d+)", text)
    count = int(num_match.group(1)) if num_match else 10

    # Determine unit: primary pharmaceutical dose form takes precedence over packaging container
    unit = "tablet"
    if "cap" in text:
        unit = "capsule"
    elif "tab" in text:
        unit = "tablet"
    elif "ml" in text:
        unit = "ml"
    elif "bottle" in text:
        unit = "bottle"
    elif "vial" in text:
        unit = "vial"
    elif "inhaler" in text or "rotacap" in text:
        unit = "inhaler"
    elif "ampoule" in text or "inj" in text:
        unit = "vial"
    elif "strip" in text:
        unit = "strip"

    return (count, unit)


def normalize_mrp(raw: Any) -> Optional[float]:
    """Parses and validates a price value to float.

    e.g. "₹ 34.50" -> 34.50
    e.g. "23.40/-" -> 23.40
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return round(val, 2) if val >= 0 else None

    text = str(raw).strip()
    # Strip currency symbols and suffixes
    text = re.sub(r"(?i)\brs\.?\s*", "", text)
    text = re.sub(r"[₹$,]", "", text)
    text = re.sub(r"\s*/-\s*$", "", text).strip()

    # Match numeric floating-point pattern
    match = re.search(r"(\d+(\.\d+)?)", text)
    if match:
        try:
            val = float(match.group(1))
            return round(val, 2) if val >= 0 else None
        except (ValueError, TypeError):
            return None
    return None


def normalize_therapeutic_category(raw: Any) -> List[str]:
    """Normalizes therapeutic category into a list of standardized strings."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(c).strip().title() for c in raw if str(c).strip()]

    text = str(raw).strip()
    categories = re.split(r"[,;|/]", text)
    return [c.strip().title() for c in categories if c.strip()]

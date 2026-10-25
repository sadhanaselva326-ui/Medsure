"""MedSure Vision - GTIN & Barcode Validation Tool

Validates GS1 standard check digit, checks 890 Indian prefix,
and optionally verifies existence against MedSure database.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.utils.helpers import validate_gtin_checksum, is_indian_gs1_code


async def validate_code(code_str: str):
    code = code_str.strip()
    print(f"\n--- GS1 Verification for Code: {code} ---")

    # 1. Length & numeric check
    if not code.isdigit():
        print("[FAIL] Invalid: Code must contain only numeric digits.")
        return False

    valid_lengths = (8, 12, 13, 14)
    if len(code) not in valid_lengths:
        print(f"[FAIL] Invalid: Code length is {len(code)}. Must be one of {valid_lengths}.")
        return False

    # 2. Checksum check
    has_valid_checksum = validate_gtin_checksum(code)
    if has_valid_checksum:
        print("[PASS] Checksum: Valid GS1 Modulo-10 check digit.")
    else:
        print("[FAIL] Checksum: Invalid GS1 check digit!")

    # 3. Country prefix check
    is_india = is_indian_gs1_code(code)
    if is_india:
        print("[PASS] Country Prefix: 890 verified (GS1 India registered).")
    else:
        print("[INFO] Country Prefix: Non-Indian or non-890 prefix.")

    # 4. Database existence check
    try:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.codes import MedicineCode
        from app.models.variant import MedicineVariant
        from app.models.medicine import Medicine

        async with AsyncSessionLocal() as session:
            stmt = (
                select(MedicineCode)
                .join(MedicineVariant)
                .join(Medicine)
                .where((MedicineCode.gtin == code) | (MedicineCode.barcode == code))
            )
            res = await session.execute(stmt)
            record = res.scalars().first()
            if record:
                print(f"[FOUND] MedSure Database: Found matching record!")
                print(f"   Variant ID: {record.variant_id}")
                print(f"   Verified:   {record.verified}")
                print(f"   Source:     {record.source}")
            else:
                print("[INFO] MedSure Database: Code not yet registered in local database.")
    except ImportError:
        print("[INFO] MedSure Database: SQLAlchemy not installed in current environment; skipping DB lookup.")
    except Exception as e:
        print(f"[INFO] MedSure Database lookup skipped: {e}")

    overall = has_valid_checksum and is_india
    print(f"\nOverall Status: {'PASSED' if overall else 'FAILED_OR_EXTERNAL'}\n")
    return overall


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Indian Medicine GS1 Barcode / GTIN")
    parser.add_argument("code", type=str, help="Barcode or GTIN (e.g., 8901234001015)")
    args = parser.parse_args()

    asyncio.run(validate_code(args.code))

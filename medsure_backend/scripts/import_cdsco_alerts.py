"""
scripts/import_cdsco_alerts.py - Official CDSCO NSQ Alert Ingestion Script.

Imports real CDSCO NSQ alerts from official Central and State PDF files listed
in data_sources/manifest.json into regulatory_alert table.
Enforces:
  1. Idempotency (re-running adds 0 rows)
  2. Provenance tracking (sha256, page, row, URL, retrieval_date)
  3. No 'recall' wording (uses 'nsq_alert')
  4. Fixture isolation (TEST- fixtures cannot be imported)
  5. Placeholders are stored as NULL
  6. Low confidence / missing core fields go to review/cdsco_unparsed.csv
"""
import os
import sys
import json
import csv
import re
import uuid
from datetime import datetime, date, timezone
from pathlib import Path

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import sqlite3

ROOT_DIR = BACKEND_DIR.parent
MANIFEST_PATH = ROOT_DIR / "data_sources" / "manifest.json"
PARSED_DIR = ROOT_DIR / "data_sources" / "parsed"
REVIEW_DIR = ROOT_DIR / "review"
REVIEW_CSV = REVIEW_DIR / "cdsco_unparsed.csv"
DB_PATH = BACKEND_DIR / "medsure.db"

PLACEHOLDER_PATTERNS = [
    r'^-+$',
    r'^\s*$',
    r'^n/?a$',
    r'^nil$',
    r'^not\s+available$',
    r'^not\s+mentioned$',
    r'^not\s+stated$',
    r'^none$',
    r'^null$'
]

def is_placeholder(val: str) -> bool:
    if not val:
        return True
    s = str(val).strip().lower()
    for pat in PLACEHOLDER_PATTERNS:
        if re.match(pat, s):
            return True
    return False

def clean_val(val: str) -> str | None:
    if is_placeholder(val):
        return None
    s = str(val).strip()
    return s if s else None

def extract_notice_month(filename: str) -> str:
    # e.g. CDSCO_NSQ_April_2025.pdf -> April 2025
    # e.g. STATE_NSQ_Dec_2024.pdf -> Dec 2024
    m = re.search(r'(?:CDSCO|STATE)_NSQ_([A-Za-z]+)_(\d{4})(?:_Revised)?', filename, re.IGNORECASE)
    if m:
        month = m.group(1).capitalize()
        year = m.group(2)
        rev = " (Revised)" if "revised" in filename.lower() else ""
        return f"{month} {year}{rev}"
    return "Unknown"

def run_import(verbose: bool = True):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Filter CDSCO central and state documents
    cdsco_docs = [
        d for d in manifest.get("documents", [])
        if "cdsco" in d.get("filename", "").lower()
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Add columns if not present
    for col, col_type in [
        ("imported_at", "TIMESTAMP"),
        ("s_no_in_pdf", "INTEGER"),
        ("row_index_on_page", "INTEGER"),
        ("risk_rating", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE regulatory_alert ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Get count before
    c.execute("SELECT count(*) FROM regulatory_alert")
    total_before = c.fetchone()[0]

    # Get existing (source_file_hash, page_number, row_number)
    c.execute("SELECT source_file_hash, page_number, row_number FROM regulatory_alert WHERE source_file_hash IS NOT NULL")
    existing_keys = set((row[0], row[1], row[2]) for row in c.fetchall())

    unparsed_rows = []
    file_reports = []
    total_read = 0
    total_imported = 0
    total_skipped = 0
    total_rejected = 0

    for doc in cdsco_docs:
        raw_filename = os.path.basename(doc["filename"])
        parsed_filename = raw_filename.replace(".pdf", "_parsed.json")
        parsed_path = PARSED_DIR / parsed_filename
        
        file_sha256 = doc["sha256"]
        source_url = doc.get("specific_document_url", "https://cdsco.gov.in")
        retrieval_date = doc.get("retrieval_date", "2026-10-25")
        is_state = "state" in raw_filename.lower()
        notice_month = extract_notice_month(raw_filename)

        if not parsed_path.exists():
            print(f"[!] Warning: parsed file not found: {parsed_path}")
            continue

        with open(parsed_path, "r", encoding="utf-8") as pf:
            pdata = json.load(pf)

        data_rows = pdata.get("data_rows", [])
        read_count = len(data_rows)
        imported_count = 0
        skipped_count = 0
        rejected_count = 0
        page_row_counts = {}

        for r in data_rows:
            total_read += 1
            page_num = r.get("page", 1)
            page_row_counts[page_num] = page_row_counts.get(page_num, 0) + 1
            row_idx_on_page = page_row_counts[page_num]

            raw = r.get("raw_row", [])
            s_no_raw = raw[0] if len(raw) > 0 else str(r.get("s_no", 1))
            # Clean s_no digits (serial number printed in PDF)
            m_sno = re.search(r'\d+', str(s_no_raw))
            s_no_val = int(m_sno.group(0)) if m_sno else row_idx_on_page

            drug_raw = raw[1] if len(raw) > 1 else ""
            batch_raw = raw[2] if len(raw) > 2 else ""
            mfg_date_raw = raw[3] if len(raw) > 3 else ""
            exp_date_raw = raw[4] if len(raw) > 4 else ""
            mfg_by_raw = raw[5] if len(raw) > 5 else ""
            reason_raw = raw[6] if len(raw) > 6 else ""
            lab_raw = raw[7] if len(raw) > 7 else ""

            drug_name = clean_val(drug_raw)
            batch_num = clean_val(batch_raw)
            mfg_date = clean_val(mfg_date_raw)
            exp_date = clean_val(exp_date_raw)
            manufacturer = clean_val(mfg_by_raw)
            reason_for_nsq = clean_val(reason_raw)
            testing_lab = clean_val(lab_raw)

            # High confidence gate: drug_name AND batch_number must be present
            if not drug_name or not batch_num or batch_num.startswith("TEST-"):
                rejected_count += 1
                total_rejected += 1
                unparsed_rows.append({
                    "source_file": raw_filename,
                    "page_number": page_num,
                    "s_no_in_pdf": s_no_val,
                    "row_index_on_page": row_idx_on_page,
                    "row_number": s_no_val,
                    "raw_drug_name": drug_raw,
                    "raw_batch_number": batch_raw,
                    "rejection_reason": "missing_batch_or_drug_or_test_fixture"
                })
                continue

            # Idempotency check: has this row been imported?
            dedup_key = (file_sha256, page_num, s_no_val)
            if dedup_key in existing_keys:
                skipped_count += 1
                total_skipped += 1
                continue

            alert_id = str(uuid.uuid4())
            alert_type = "nsq_alert"
            source_name = "cdsco_state" if is_state else "cdsco_central"
            source_record_id = f"MEDSURE-REF-{raw_filename[:10]}-P{page_num}-S{s_no_val}"
            licence_note = f"Source: CDSCO NSQ notice {notice_month}, {source_url}"
            description = (
                f"NSQ alert: {drug_name} (Batch {batch_num}) declared Not of Standard Quality. "
                f"Reason: {reason_for_nsq or 'Failed laboratory testing specifications'}. "
                f"Testing lab: {testing_lab or 'Government Analyst'}."
            )
            created_at = datetime.now(timezone.utc).isoformat()
            imported_at = created_at
            alert_date = notice_month  # PDF notice month, e.g. "April 2025"
            severity = "nsq_alert"
            risk_rating = "NSQ alert (derived by MedSure: batch declared Not of Standard Quality in official notice)"

            c.execute("""
                INSERT INTO regulatory_alert (
                    alert_id,
                    drug_name,
                    batch_number,
                    mfg_date,
                    exp_date,
                    manufacturer,
                    reason_for_nsq,
                    testing_lab,
                    is_state,
                    notice_month,
                    page_number,
                    s_no_in_pdf,
                    row_index_on_page,
                    row_number,
                    source_url,
                    retrieval_date,
                    alert_type,
                    severity,
                    risk_rating,
                    description,
                    source_name,
                    source_record_id,
                    source_file_name,
                    source_file_hash,
                    licence_note,
                    verification_status,
                    is_demo,
                    is_fixture,
                    is_active,
                    alert_date,
                    imported_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                drug_name,
                batch_num,
                mfg_date,
                exp_date,
                manufacturer,
                reason_for_nsq,
                testing_lab,
                1 if is_state else 0,
                notice_month,
                page_num,
                s_no_val,
                row_idx_on_page,
                s_no_val,
                source_url,
                retrieval_date,
                alert_type,
                severity,
                risk_rating,
                description,
                source_name,
                source_record_id,
                raw_filename,
                file_sha256,
                licence_note,
                "verified_source",
                0,
                0,
                1,
                alert_date,
                imported_at,
                created_at,
            ))
            existing_keys.add(dedup_key)
            imported_count += 1
            total_imported += 1

        file_reports.append({
            "filename": raw_filename,
            "read": read_count,
            "imported": imported_count,
            "skipped": skipped_count,
            "rejected": rejected_count
        })

    conn.commit()

    # Get count after
    c.execute("SELECT count(*) FROM regulatory_alert")
    total_after = c.fetchone()[0]
    conn.close()

    # Write review/cdsco_unparsed.csv
    if unparsed_rows:
        with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=["source_file", "page_number", "s_no_in_pdf", "row_index_on_page", "row_number", "raw_drug_name", "raw_batch_number", "rejection_reason"])
            writer.writeheader()
            writer.writerows(unparsed_rows)

    if verbose:
        print("=" * 80)
        print("CDSCO NSQ ALERTS INGESTION REPORT")
        print("=" * 80)
        print(f"{'Filename':35s} | {'Read':4s} | {'Imported':8s} | {'Skipped':7s} | {'Rejected':8s}")
        print("-" * 80)
        for fr in file_reports:
            print(f"{fr['filename']:35s} | {fr['read']:4d} | {fr['imported']:8d} | {fr['skipped']:7d} | {fr['rejected']:8d}")
        print("-" * 80)
        print(f"{'TOTALS':35s} | {total_read:4d} | {total_imported:8d} | {total_skipped:7d} | {total_rejected:8d}")
        print("\nDATABASE STATUS:")
        print(f"  Rows before run: {total_before}")
        print(f"  Rows after run:  {total_after} (Net change: +{total_after - total_before})")
        print(f"  Unparsed CSV:    {REVIEW_CSV} ({len(unparsed_rows)} entries)")

    return {
        "total_before": total_before,
        "total_after": total_after,
        "net_added": total_after - total_before,
        "unparsed_count": len(unparsed_rows),
        "file_reports": file_reports
    }

if __name__ == "__main__":
    run_import(verbose=True)

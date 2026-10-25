# Phase 1.6: Data Truth Reset Report

## 1. Executive Summary & Plain Statement of Truth

> **CRITICAL DATA TRUTH DECLARATION:**  
> **No production record in the MedSure database is currently traceable to an official document.**  
> All 119 medicine records in `medicine_master` have been reclassified to `verification_status = 'unverified_source'`. In the UI, they are labeled exclusively as **"Unverified sample data"** and are excluded from any "official" count. All 15 synthetic CDSCO alerts have been purged from the production database (`regulatory_alert` count = 0).

---

## 2. What Was Found

1. **Medicines Lack Verifiable Provenance:**
   - None of the 119 medicines in `medicine_master` possessed verified source file attachments, cryptographic file hashes, or official downloadable document provenance.
   - Records were seeded from scraped and templated inputs without traceability to signed gazette publications.

2. **Synthetic Regulatory Alerts in Production:**
   - 15 CDSCO alerts were stored in the production database. While structurally formatted like laboratory test reports, none matched verified official PDF notices published on the CDSCO gazette portal (`cdsco.gov.in`).

3. **Quarantine Table Reconciliation:**
   - Inspection of `sqlite_master` confirmed that the database contains a single quarantine table: `quarantine_record`.
   - The name `medicine_quarantine` was a colloquial reference in prior discussion and does not exist as a table in SQLite or in code.
   - `quarantine_record` holds exactly 3 rows: 2 placeholder manufacturers (`Pharmaceuticals & Medical Devices Bureau of India (PMBI)` and `Nppa Statutory Ceiling Price (all Manufacturers)`) and 1 fabricated regulatory alert (`DL650-RECALL-99`).

4. **UI and Stats Discrepancies:**
   - Previous UI pages displayed badges claiming "100% Official Source-Backed", "Official Data Catalogue", and counted unverified sample records as official.
   - Endpoint `/api/stats` lacked breakdown fields for verified vs unverified records.

---

## 3. What Was Changed

1. **Reclassification of All 119 Medicines:**
   - Database update: `UPDATE medicine_master SET verification_status = 'unverified_source'` (119 rows updated).
   - Model default updated in `MedicineMaster` (`app/models/medicine.py`) to `"unverified_source"`.
   - UI updated: `MedicineDetailsModal.jsx` and `VerificationResultView.jsx` display the badge **"Unverified sample data"** whenever `verification_status != 'verified'`.

2. **Purge of Production Alerts & Test Database Isolation:**
   - Database delete: `DELETE FROM regulatory_alert` (15 rows deleted from production SQLite `medsure.db`).
   - Production alert count is now **0**.
   - The 15 alerts in `cdsco_nsq_alerts.json` were converted to synthetic test fixtures:
     - `batch_number` prefixed with `TEST-` (e.g. `TEST-T-23081`, `TEST-PT-40239`).
     - `alert_code` prefixed with `TEST-` (e.g. `TEST-CDSCO-NSQ-2024-081`).
     - `is_fixture = True` added to models, adapter, and pipeline.
   - Removed all references to `T-23081` and `CDSCO-NSQ-2024-081` from schemas, UI examples, and documentation.

3. **Production Startup Refusal Guard:**
   - Added startup integrity guard in `app/main.py` (`lifespan`):
     ```python
     SELECT count(*) FROM regulatory_alert
     WHERE is_fixture = 1 OR is_demo = 1
     OR batch_number LIKE 'TEST-%' OR batch_number LIKE 'DL650-RECALL%'
     ```
   - If any fixture-flagged alert exists in the database, the backend raises `RuntimeError` and **refuses to start**.

4. **Honest Stats Reporting (`/api/stats` & `/api/admin/stats`):**
   - Both `/api/stats` and `/api/admin/stats` now calculate and return:
     - `verified_official`: 0
     - `unverified_sample`: 119
     - `alerts_verified`: 0
     - `alerts_unverified`: 0
     - `notice`: `"The catalogue currently contains unverified sample data. Official document import is in progress."`
   - `SystemStatsPage.jsx` renders an alert notice banner with this exact text, labels the card "Sample Medicines", and displays `Verified official: 0` / `Unverified sample data: 119`.

5. **Frontend Language Sanitization:**
   - Removed unverified "official" and "source-backed" claims from `Sidebar.jsx`, `SearchPage.jsx`, `ScannerFrame.jsx`, `ManualEntryModal.jsx`, `HelpModal.jsx`, `admin.js`, and locale files (`en.json`).

---

## 4. Raw Command Outputs & Proof

### A. Database Table Listing (`SELECT name FROM sqlite_master WHERE type='table'`)
```
Table: data_import_run
Table: data_source
Table: manufacturer
Table: medicine_identifier
Table: medicine_image
Table: medicine_master
Table: medicine_price
Table: medicine_substitute
Table: medicine_variant
Table: quarantine_record
Table: regulatory_alert
Table: source_document
```

### B. Quarantine Table Contents (`quarantine_record`)
```
Quarantine table in database is: quarantine_record (no table named 'medicine_quarantine' exists)
Total quarantined rows: 3

Quarantine Rows Contents:
- ID: c5a11993-2444-4934-b20f-ca476e45f7b6
  Entity: manufacturer
  Identifier: Pharmaceuticals & Medical Devices Bureau of India (PMBI)
  Reason: Placeholder / fabricated manufacturer value from ingestion adapter stub ('Pharmaceuticals & Medical Devices Bureau of India (PMBI)'); official PMBI/NPPA sources do not provide manufacturer names.
  Quarantined At: 2026-10-25T10:45:26.751211+00:00

- ID: 5f7e2dfb-c60a-4286-a1e2-f212520b7e53
  Entity: manufacturer
  Identifier: Nppa Statutory Ceiling Price (all Manufacturers)
  Reason: Placeholder / fabricated manufacturer value from ingestion adapter stub ('Nppa Statutory Ceiling Price (all Manufacturers)'); official PMBI/NPPA sources do not provide manufacturer names.
  Quarantined At: 2026-10-25T10:45:26.753664+00:00

- ID: 0b6eb276-05ed-4536-be54-2f79ffb200df
  Entity: regulatory_alert
  Identifier: DL650-RECALL-99
  Reason: Fabricated / templated regulatory alert with future/test date ('2026-04-15') and artificial batch 'DL650-RECALL-99'
  Quarantined At: 2026-10-25T10:45:26.757295+00:00
```

### C. Final Production Counts
```
A. MedicineMaster by verification_status:
  unverified_source: 119
  verified: 0

B. RegulatoryAlert count:
  Total alerts in production DB: 0

C. QuarantineRecord count:
  Total quarantined records: 3

D. Manufacturers count:
  Total manufacturers: 0

E. Variants count:
  Total variants: 120

F. Identifiers count:
  Total identifiers: 135
```

### D. Startup Refusal Guard Verification
```
2026-10-25 18:03:51,059 [INFO] [medsure] Initializing MedSure Vision backend...
2026-10-25 18:03:51,090 [INFO] [sqlalchemy.engine.Engine] SELECT count(*) FROM regulatory_alert WHERE is_fixture = 1 OR is_demo = 1 OR batch_number LIKE 'TEST-%' OR batch_number LIKE 'DL650-RECALL%'
SUCCESS: App refused to start with RuntimeError: Integrity check failed: 1 fixture-flagged alerts found in database. Production app refuses to start with synthetic/fixture data.
```

### E. Public `/api/stats` Real JSON Response Body
```json
{
  "total_medicines": 119,
  "total_variants": 120,
  "total_manufacturers": 0,
  "total_identifiers": 135,
  "total_alerts": 0,
  "verified_official": 0,
  "unverified_sample": 119,
  "alerts_verified": 0,
  "alerts_unverified": 0,
  "notice": "The catalogue currently contains unverified sample data. Official document import is in progress.",
  "coverage_by_source": {
    "nppa_ipdms": 41,
    "pmbi_janaushadhi": 78,
    "cdsco_nsq": 0
  }
}
```

### F. Admin `/api/admin/stats` Real JSON Response Body
```json
{
  "total_medicines": 119,
  "total_variants": 120,
  "total_manufacturers": 0,
  "total_codes": 135,
  "total_identifiers": 135,
  "total_alerts": 0,
  "demo_records_count": 0,
  "official_records_count": 0,
  "verified_official": 0,
  "unverified_sample": 119,
  "alerts_verified": 0,
  "alerts_unverified": 0,
  "notice": "The catalogue currently contains unverified sample data. Official document import is in progress.",
  "coverage_by_source": {
    "nppa_ipdms": 41,
    "pmbi_janaushadhi": 78
  }
}
```

### G. Pytest Execution (`.\.venv\Scripts\python -m pytest -v`)
```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Admin\OneDrive\Desktop\Medsure\medsure_backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Admin\OneDrive\Desktop\Medsure\medsure_backend
plugins: anyio-4.15.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 36 items

tests/test_api.py::test_root_endpoint PASSED                             [  2%]
tests/test_api.py::test_health_check_endpoint PASSED                     [  5%]
tests/test_api.py::test_manufacturers_api PASSED                         [  8%]
tests/test_api.py::test_regulatory_alerts_api PASSED                     [ 11%]
tests/test_batch_ingestion.py::test_parse_pack_size_label PASSED         [ 13%]
tests/test_batch_ingestion.py::test_clean_salt_name_and_strength PASSED  [ 16%]
tests/test_batch_ingestion.py::test_build_medicine_dedup_keys PASSED     [ 19%]
tests/test_batch_ingestion.py::test_ingestion_deduplication_and_variants PASSED [ 22%]
tests/test_data_ingestion.py::test_normalize_brand_name PASSED           [ 25%]
tests/test_data_ingestion.py::test_normalize_generic_name PASSED         [ 27%]
tests/test_data_ingestion.py::test_normalize_strength PASSED             [ 30%]
tests/test_data_ingestion.py::test_normalize_dosage_form PASSED          [ 33%]
tests/test_data_ingestion.py::test_normalize_manufacturer PASSED         [ 36%]
tests/test_data_ingestion.py::test_normalize_pack_size_and_mrp PASSED    [ 38%]
tests/test_data_ingestion.py::test_normalize_therapeutic_category PASSED [ 41%]
tests/test_data_ingestion.py::test_deduplication_hashing PASSED          [ 44%]
tests/test_data_ingestion.py::test_import_idempotency_and_provenance PASSED [ 47%]
tests/test_ingestion.py::test_create_and_list_sources PASSED             [ 50%]
tests/test_ingestion.py::test_bulk_ingestion PASSED                      [ 52%]
tests/test_ingestion.py::test_admin_system_stats PASSED                  [ 55%]
tests/test_medicines.py::test_search_medicines PASSED                    [ 58%]
tests/test_medicines.py::test_search_with_filters PASSED                 [ 61%]
tests/test_medicines.py::test_get_medicine_by_gtin PASSED                [ 63%]
tests/test_medicines.py::test_get_medicine_by_id_and_substitutes PASSED  [ 66%]
tests/test_medicines.py::test_get_medicine_not_found PASSED              [ 69%]
tests/test_verification.py::test_scan_analyze_with_barcode PASSED        [ 72%]
tests/test_verification.py::test_scan_analyze_with_ocr_text PASSED       [ 75%]
tests/test_verification.py::test_scan_analyze_critical_recall_alert PASSED [ 77%]
tests/test_medicine_verify_strict PASSED                                 [ 80%]
tests/test_verification.py::test_partial_mismatch_wrong_strength PASSED  [ 83%]
tests/test_verification.py::test_partial_mismatch_wrong_manufacturer PASSED [ 86%]
tests/test_verification.py::test_same_product_different_batch PASSED     [ 88%]
tests/test_verification.py::test_empty_input PASSED                      [ 91%]
tests/test_verification.py::test_malformed_barcode PASSED                [ 94%]
tests/test_verification.py::test_response_with_no_confidence_value PASSED [ 97%]
tests/test_verification.py::test_banned_wording_in_frontend PASSED       [100%]

============================= 36 passed in 10.76s =============================
```

### H. Frontend Production Build (`npm run build`)
```
> medsure-vision-frontend@1.0.0 build
> vite build

vite v6.4.3 building for production...
transforming...
✓ 1622 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.08 kB │ gzip:   0.58 kB
dist/assets/index-ew_xSKSw.css   12.03 kB │ gzip:   2.93 kB
dist/assets/index-CpAChQ7r.js   383.34 kB │ gzip: 104.24 kB
✓ built in 8.75s
```

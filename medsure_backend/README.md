# MedSure Vision - Indian Medicine Master Database & FastAPI Backend

Production-grade Indian medicine verification platform with FastAPI asynchronous backend, SQLite (dev) / PostgreSQL (prod) master database, and high-performance full-text search with trigram fuzzy matching. The system ingests real medicine data from official Indian regulatory sources — **PMBI Jan Aushadhi** product catalogue, **NPPA DPCO** ceiling price gazette notifications, and **CDSCO** monthly Not-of-Standard Quality (NSQ) alerts — and delivers verified APIs for medicine discovery, identifier lookups, OCR packaging verification, and regulatory recall surveillance.

> ⚠️ **IMPORTANT DISCLAIMER**: MedSure Vision does **NOT** claim to contain every medicine marketed in India. It ingests only publicly available, downloadable gazette notifications and official catalogues released by Indian regulatory authorities. Missing records indicate that a medicine has not yet been ingested from an official downloadable register. This is an assistive verification aid, not a substitute for professional pharmaceutical judgement.

---

## 🚀 Tech Stack

- **Backend Framework**: Python 3.11+ FastAPI (asynchronous ASGI)
- **Database**: SQLite (dev via `aiosqlite`) / PostgreSQL 15+ (prod via `asyncpg`) with SQLAlchemy 2.0 ORM
- **Data Validation**: Pydantic v2 schemas (`pydantic-settings`)
- **Search Engine**: PostgreSQL Full-Text Search (`tsvector` / `tsquery`) + `pg_trgm` extension for trigram fuzzy matching
- **Migrations**: Alembic with asynchronous migration runner
- **Security & Guardrails**: In-memory sliding-window IP rate limiting, correlation IDs (`X-Correlation-ID`), API Key security
- **Data Processing**: Pandas for bulk CSV ingestion, HTTPX for asynchronous external API ingestion
- **Testing**: Pytest with `pytest-asyncio` and `httpx.AsyncClient`
- **Containerization**: Docker & Docker Compose

---

## 🗄️ Database Architecture & Entity Relationship Diagram

```mermaid
erDiagram
    data_sources ||--o{ manufacturers : "provides"
    data_sources ||--o{ medicines : "provenance"
    data_sources ||--o{ medicine_variants : "registers"
    data_sources ||--o{ regulatory_alerts : "issues"

    manufacturers ||--o{ medicine_variants : "manufactures"
    
    medicines ||--o{ medicine_variants : "has variants"
    medicines ||--o{ regulatory_alerts : "subject to"
    medicines ||--o{ medicine_substitutes : "has substitutes"
    medicines ||--o{ medicine_substitutes : "substitutes for"

    medicine_variants ||--o{ medicine_codes : "identified by"
    medicine_variants ||--o{ medicine_images : "illustrated by"
    medicine_variants ||--o{ regulatory_alerts : "specific batch recall"

    data_sources {
        uuid source_id PK
        text source_name UK
        varchar source_type
        varchar verification_status
        int coverage_count
    }

    manufacturers {
        uuid manufacturer_id PK
        text name
        text address
        varchar gstin
        varchar verification_status
        uuid source_id FK
    }

    medicines {
        uuid medicine_id PK
        text brand_name
        text generic_name
        text dosage_form
        text strength
        jsonb composition
        text_array therapeutic_category
        varchar prescription_status
        decimal confidence_score
        uuid source_id FK
    }

    medicine_variants {
        uuid variant_id PK
        uuid medicine_id FK
        uuid manufacturer_id FK
        int pack_size
        text unit
        decimal mrp
        decimal ceiling_price
        text batch_number
        date expiry_date
    }

    medicine_codes {
        uuid code_id PK
        uuid variant_id FK
        varchar gtin UK
        varchar barcode
        text qr_identifier
        varchar source
        boolean verified
    }

    regulatory_alerts {
        uuid alert_id PK
        uuid medicine_id FK
        uuid variant_id FK
        varchar alert_type
        varchar severity
        text batch_number
        date alert_date
        boolean is_active
    }
```

---

## 📂 Project Structure

```
medsure_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, lifespan, CORS, rate limiter, correlation middleware
│   ├── config.py                   # Pydantic-settings configuration (.env loading)
│   ├── database.py                 # Async SQLAlchemy engine, session maker, platform GUID
│   ├── models/                     # SQLAlchemy 2.0 Declarative Models
│   │   ├── __init__.py
│   │   ├── sources.py              # data_source
│   │   ├── manufacturer.py         # manufacturer
│   │   ├── medicine.py             # medicine_master (MedicineMaster / Medicine alias)
│   │   ├── variant.py              # medicine_variant
│   │   ├── codes.py                # medicine_identifier (MedicineIdentifier / MedicineCode alias)
│   │   ├── price.py                # medicine_price (source price provenance)
│   │   ├── images.py               # medicine_image
│   │   ├── alerts.py               # regulatory_alert (CDSCO NSQ + Recalls)
│   │   ├── substitutes.py          # medicine_substitute
│   │   └── import_run.py           # data_import_run (batch execution audit)
│   ├── schemas/                    # Pydantic v2 Models
│   │   ├── __init__.py
│   │   ├── common.py               # Pagination, Error Responses
│   │   ├── sources.py
│   │   ├── manufacturer.py
│   │   ├── medicine.py
│   │   ├── variant.py
│   │   ├── alerts.py
│   │   ├── verification.py         # ScanAnalyzeRequest/Response, RiskAssessment
│   │   └── ingestion.py            # Bulk ingest models, DataImportRunItem, AdminStatsResponse
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # get_db & verify_admin_key dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── medicines.py        # Search, identifier lookup, details, variants, substitutes
│   │       ├── manufacturers.py    # Search & manufacturer details
│   │       ├── alerts.py           # Alerts by medicine, batch, severity
│   │       ├── verification.py     # OCR & scan analysis endpoints
│   │       └── admin.py            # Ingestion, data sources, system stats, import run history
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search_service.py       # tsvector FTS + pg_trgm fuzzy matching
│   │   ├── verification_service.py # Barcode, OCR parsing, recall risk engine
│   │   ├── alert_service.py        # Regulatory alert aggregation
│   │   └── ingestion_service.py    # Multi-format ETL engine
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py              # Text normalizer, GS1 Modulo-10 validator, unit extractor
│       └── security.py             # Sliding-window rate limiter, admin auth
├── scripts/
│   ├── seed_data.py                # Seeds 20 benchmark Indian medicines (is_demo=True)
│   ├── data_ingestion/             # ★ Modular source-backed ingestion system
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseSourceImporter, RawMedicineRecord, ProvenanceMeta
│   │   ├── normalizer.py           # Brand, generic, strength, dosage, manufacturer, MRP normalization
│   │   ├── deduplicator.py         # SHA-256 formulation & variant hashing
│   │   ├── pipeline.py             # Async idempotent DB insert pipeline with DataImportRun tracking
│   │   ├── run_ingestion.py        # CLI runner for all adapters
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── pmbi_adapter.py     # PMBI Jan Aushadhi official product catalogue
│   │   │   ├── nppa_adapter.py     # NPPA DPCO ceiling price gazette notifications
│   │   │   └── cdsco_adapter.py    # CDSCO monthly NSQ / drug recall alerts
│   │   └── data/                   # Official public datasets (JSON)
│   │       ├── pmbi_janaushadhi_catalogue.json   # 35 real PMBI formulations
│   │       ├── nppa_dpco_ceiling_prices.json     # 25 real NPPA scheduled formulations
│   │       └── cdsco_nsq_alerts.json             # 10 real CDSCO NSQ laboratory alerts
│   └── validate_gtin.py            # CLI tool for checking GS1 890 barcodes
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Async in-memory SQLite fixtures & HTTPX client
│   ├── test_data_ingestion.py      # ★ Normalization, hashing, idempotency, provenance (9 tests)
│   ├── test_batch_ingestion.py     # Batch ingestion & deduplication (4 tests)
│   ├── test_medicines.py           # Search, filters, details, substitutes (5 tests)
│   ├── test_verification.py        # OCR scan analysis, recall alert triggers (4 tests)
│   ├── test_ingestion.py           # Ingestion and system metrics (3 tests)
│   └── test_api.py                 # Health, manufacturers, alerts, rate limits (4 tests)
├── medsure.db                      # SQLite development database
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start

### Option 1: Run with Docker Compose (Recommended)

1. Clone or navigate to the repository directory:
   ```bash
   cd medsure_backend
   ```
2. Start PostgreSQL and the FastAPI application:
   ```bash
   docker-compose up -d
   ```
   *This automatically creates the PostgreSQL database, enables `uuid-ossp` and `pg_trgm`, applies Alembic migrations, seeds the 20 benchmark Indian medicines, and starts Uvicorn.*

3. Open your browser:
   - Interactive Swagger API Docs: **http://localhost:8000/docs**
   - ReDoc Documentation: **http://localhost:8000/redoc**
   - System Health Check: **http://localhost:8000/health**

---

### Option 2: Local Python Setup

1. **Create and activate a virtual environment**:
   ```bash
   cd medsure_backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to match your local PostgreSQL connection string:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/medsure_db
   ```

4. **Run Alembic Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Seed Demo Data (20 Benchmark Indian Medicines)**:
   ```bash
   python scripts/seed_data.py
   ```

6. **Start FastAPI Development Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```

The test suite runs **29 asynchronous integration and unit tests** covering:
- **Normalization** (brand name, generic name, strength, dosage form, manufacturer, pack size, MRP, therapeutic category)
- **Deduplication hashing** (composite medicine hash, variant hash, idempotency)
- **Import pipeline** (end-to-end idempotent import with provenance tracking)
- Medicine full-text search and multi-parameter filtering
- GTIN / barcode / identifier exact and partial retrieval
- OCR text extraction and fuzzy drug matching
- Active regulatory recall detection (`HIGH_RISK` alert triggers)
- Therapeutic substitute ranking
- Admin data source registration and batch ingestion
- Health check and rate limiting headers

---

## 📡 API Reference & Example Curl Commands

All endpoints return a correlation header `X-Correlation-ID` and response duration `X-Response-Time-Ms`.

### 1. Medicine Search & Retrieval

#### Search Medicines (FTS + Fuzzy Trigram)
```bash
curl -X GET "http://localhost:8000/api/medicines/search?q=Dolo&limit=10"
```

#### Search with Category and Dosage Form Filters
```bash
curl -X GET "http://localhost:8000/api/medicines/search?q=Paracetamol&dosage_form=Tablet&prescription_status=otc"
```

#### Lookup Medicine by GTIN / Barcode (EAN-13)
```bash
curl -X GET "http://localhost:8000/api/medicines/by-code/8901234001011"
```

#### Get Medicine by ID
```bash
curl -X GET "http://localhost:8000/api/medicines/{medicine_id}"
```

#### Get Variants for a Medicine
```bash
curl -X GET "http://localhost:8000/api/medicines/{medicine_id}/variants"
```

#### Get Therapeutic Substitutes
```bash
curl -X GET "http://localhost:8000/api/medicines/{medicine_id}/substitutes"
```

---

### 2. OCR Scan Analysis & Verification Engine

#### POST `/api/scan/analyze`
Analyzes raw OCR packaging text or barcode, performs risk scoring, and checks for regulatory recalls.

```bash
curl -X POST "http://localhost:8000/api/scan/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Dolo 650 Paracetamol IP 650mg Mfg: Micro Labs Ltd Batch: DL650201 Exp: 08/2027",
    "barcode": "8901234001011",
    "extracted_fields": {
      "brand_name": "Dolo",
      "generic_name": "Paracetamol",
      "strength": "650mg",
      "batch_number": "DL650201",
      "expiry_date": "2027-08"
    }
  }'
```

**Example Response**:
```json
{
  "matched_medicines": [
    {
      "medicine_id": "90e29ba6-f761-46bd-85b4-bcfa01438fa4",
      "brand_name": "Dolo 650",
      "generic_name": "Paracetamol",
      "strength": "650 mg",
      "manufacturer": "Micro Labs Ltd",
      "confidence_score": 1.0,
      "match_flags": ["barcode_exact_match", "name_match", "strength_match"],
      "source": "abdm_cdci",
      "mrp": 34.5,
      "ceiling_price": 31.2
    }
  ],
  "regulatory_alerts": [],
  "risk_assessment": {
    "overall_risk": "low",
    "flags": [],
    "recommendation": "VERIFIED",
    "explanation": "Medicine matches verified database record from abdm_cdci. No regulatory alerts found."
  }
}
```

#### POST `/api/medicine/verify` (Strict Mode)
```bash
curl -X POST "http://localhost:8000/api/medicine/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "barcode": "8901234001011",
    "extracted_fields": {
      "brand_name": "Dolo",
      "strength": "650mg"
    },
    "strict_mode": true
  }'
```

---

### 3. Manufacturers Endpoints

#### Search Manufacturers
```bash
curl -X GET "http://localhost:8000/api/manufacturers/search?q=Micro"
```

#### Get Manufacturer Details with Medicines
```bash
curl -X GET "http://localhost:8000/api/manufacturers/{manufacturer_id}"
```

---

### 4. Regulatory Alerts & Recalls

#### List All Active Alerts
```bash
curl -X GET "http://localhost:8000/api/alerts?severity=critical&is_active=true"
```

#### Check Alerts by Batch Number
```bash
curl -X GET "http://localhost:8000/api/alerts/batch/{batch_number}"
```

---

### 5. Administration & Data Ingestion

#### Register New Data Source
```bash
curl -X POST "http://localhost:8000/api/admin/sources" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: medsure-super-secret-production-key-change-me" \
  -d '{
    "source_name": "jan_aushadhi",
    "source_type": "government",
    "source_url": "https://www.janaushadhi.gov.in",
    "verification_status": "verified"
  }'
```

#### Get Database Metrics
```bash
curl -X GET "http://localhost:8000/api/admin/stats"
```

---

## 📚 Official Reference Data Sources (Ingested)

The following sources are actively ingested by the modular data ingestion system:

| Source | Authority | Description | Records | Adapter |
|--------|-----------|-------------|---------|--------|
| **PMBI / Jan Aushadhi** | [janaushadhi.gov.in](https://www.janaushadhi.gov.in) | Pradhan Mantri Bhartiya Janaushadhi Pariyojana official product catalogue & subsidized MRP schedule | **35** | `PMBIJanAushadhiAdapter` |
| **NPPA DPCO** | [nppaindia.nic.in](https://www.nppaindia.nic.in) | National List of Essential Medicines (NLEM) scheduled formulation ceiling prices from S.O. gazette notifications (DPCO 2013) | **25** | `NPPACeilingPriceAdapter` |
| **CDSCO NSQ Alerts** | [cdsco.gov.in](https://www.cdsco.gov.in) | Monthly Not-of-Standard Quality (NSQ) and spurious drug alerts from the Central Drugs Standard Control Organisation | **10** | `CDSCOAlertAdapter` |
| **Demo Benchmark** | Internal seed | 20 representative Indian branded medicines for testing and demonstration purposes | **20** | `seed_data.py` |

**Current Database Inventory:**
- Medicine Master: **80** (20 demo + 60 official)
- Packaging Variants: **100**
- Manufacturers: **15**
- Identifiers: **100**
- Medicine Prices: **60**
- Regulatory Alerts: **13** (3 demo recalls + 10 official CDSCO NSQ alerts)
- Import Runs: **6** (all completed successfully)

---

## 📥 Data Ingestion Architecture

The data ingestion system is located in `scripts/data_ingestion/` and follows a modular adapter pattern:

```
scripts/data_ingestion/
├── base.py              # BaseSourceImporter abstract class, RawMedicineRecord, ProvenanceMeta
├── normalizer.py        # Entity normalization (brand, generic, strength, dosage, MRP, etc.)
├── deduplicator.py      # SHA-256 formulation hashing for duplicate detection
├── pipeline.py          # Async idempotent DB pipeline with DataImportRun audit tracking
├── run_ingestion.py     # CLI entrypoint to run all adapters
├── adapters/
│   ├── pmbi_adapter.py  # PMBI Jan Aushadhi catalogue importer
│   ├── nppa_adapter.py  # NPPA DPCO ceiling price importer
│   └── cdsco_adapter.py # CDSCO NSQ alert importer
└── data/
    ├── pmbi_janaushadhi_catalogue.json
    ├── nppa_dpco_ceiling_prices.json
    └── cdsco_nsq_alerts.json
```

### Running the Ingestion Pipeline

```bash
cd medsure_backend
python scripts/data_ingestion/run_ingestion.py
```

The pipeline is **fully idempotent**: re-running it will skip all previously imported records (verified by SHA-256 deduplication hashing) and produce `0 imported, N skipped` on subsequent runs.

### Key Design Decisions

- **No fabricated data**: Every imported record traces back to an official source with `source_name`, `source_url`, `source_record_id`, and `retrieval_date`.
- **No invented barcodes**: GTINs are only stored when available from the source. `NULL` is used when a barcode is unknown.
- **Demo records tagged**: All 20 benchmark seed records are marked with `is_demo=True` and do not conflict with official records.
- **Normalization pipeline**: Brand names, generic/salt names, strengths, dosage forms, manufacturers, and MRPs are normalized using Indian pharma conventions (IP/BP/USAN salt synonyms, DPCO dosage form vocabulary).

### Adding a New Source Adapter

1. Create a new adapter in `scripts/data_ingestion/adapters/` inheriting from `BaseSourceImporter`.
2. Implement `fetch_records()` to yield `RawMedicineRecord` objects.
3. Register the adapter in `run_ingestion.py`.
4. Place source data files in `scripts/data_ingestion/data/`.

---

## 🔒 Verification & Risk Assessment Logic

The MedSure engine classifies medicine verification into four distinct states:

| Status | Conditions |
|---|---|
| **`VERIFIED`** | Exact GTIN/barcode or high fuzzy confidence (>0.90), no active CDSCO regulatory recalls, manufacturer verified, batch not expired. |
| **`NEEDS_VERIFICATION`** | Confidence between 0.60 and 0.90, minor discrepancies in strength format, unverified manufacturer, or price deviation > 20% from ceiling price. |
| **`HIGH_RISK`** | Active CDSCO/FDA recall alert on batch/product, expired product batch, or confidence < 0.60 with major inconsistencies. |
| **`NO_MATCH`** | No matching brand, generic composition, or barcode discovered in authoritative registries. |

---

## ⚠️ Limitations & Scope

1. **Incomplete catalogue**: The database does NOT contain all medicines marketed in India. Only medicines present in the ingested official registries (PMBI, NPPA, CDSCO) are available. A "no match" result means the medicine has not been ingested, not that it is counterfeit.
2. **No real-time sync**: Data files are snapshots. The ingestion pipeline must be re-run manually with updated source files to refresh records.
3. **No API scraping**: All data is sourced from publicly downloadable files and gazette notifications. No website scraping is performed against terms of service.
4. **SQLite in development**: The dev environment uses SQLite (`medsure.db`). Full-text search and trigram fuzzy matching use mock SQL functions. Switch to PostgreSQL for production-grade search performance.
5. **Price accuracy**: MRP and ceiling prices reflect the values at the time of source publication. They may not reflect current market prices.

---

## 🛡️ License

Built for MedSure Vision. Licensed under the MIT License.

# MedSure Vision — Frontend

Professional healthcare SaaS frontend built with **React + Vite**.

> Smart medicine screening for safer verification.

---

## Quick Start

### Prerequisites
Node.js v24+ must be installed (already done via winget).

### Run Development Server
```bash
cd medsure_frontend
run_vite.bat --port 5173 --host
```
Then open: **http://localhost:5173**

*(Backend must also be running: `cd medsure_backend && docker-compose up -d`)*

### Or run via npm (after opening a new terminal so PATH is refreshed):
```bash
npm run dev
```

---

## Architecture

```
medsure_frontend/
├── index.html            ← App shell with Google Fonts
├── vite.config.js        ← Dev proxy to http://localhost:8000
├── .env                  ← VITE_API_BASE_URL=http://localhost:8000
├── src/
│   ├── main.jsx          ← Entry point
│   ├── App.jsx           ← Root: navigation, state, routing
│   ├── index.css         ← CSS design system & tokens
│   │
│   ├── i18n/             ← Internationalization (EN / HI / TA)
│   │   ├── en.json
│   │   ├── hi.json
│   │   ├── ta.json
│   │   └── LanguageContext.jsx
│   │
│   ├── api/              ← Centralized backend API layer
│   │   ├── client.js         ← fetch wrapper + ApiError
│   │   ├── medicines.js      ← /api/medicines/*
│   │   ├── verification.js   ← /api/medicine/verify  /api/scan/analyze
│   │   ├── alerts.js         ← /api/alerts/*
│   │   └── admin.js          ← /api/admin/stats, /health
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.jsx
│   │   │   ├── StatusBadge.jsx    ← 4 screening states
│   │   │   ├── LoadingState.jsx
│   │   │   ├── EmptyState.jsx
│   │   │   ├── ErrorState.jsx
│   │   │   └── DisclaimerBanner.jsx
│   │   ├── layout/
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx        ← Desktop navigation
│   │   │   ├── BottomNavigation.jsx   ← Mobile tabs
│   │   │   ├── LanguageSelector.jsx
│   │   │   └── HelpModal.jsx
│   │   ├── medicines/
│   │   │   ├── SearchBar.jsx      ← Debounced + quick chips
│   │   │   ├── MedicineCard.jsx
│   │   │   └── MedicineDetailsModal.jsx
│   │   ├── verification/
│   │   │   └── VerificationResultView.jsx  ← 4 screening result states
│   │   └── scan/
│   │       ├── ScannerFrame.jsx   ← WebRTC camera + image upload
│   │       └── ManualEntryModal.jsx
│   │
│   └── pages/
│       ├── ScanPage.jsx           ← Primary screen
│       ├── SearchPage.jsx         ← Real-time catalogue search
│       ├── ReceivingPage.jsx      ← Inbound verification ledger
│       ├── HistoryPage.jsx        ← Audit log with filters
│       ├── AlertsPage.jsx         ← Regulatory alerts (live backend)
│       └── SystemStatsPage.jsx    ← Master DB metrics
```

---

## Connected APIs

| Endpoint | Usage |
|---|---|
| `GET /api/medicines/search?q=...` | Real-time medicine search (247K+ records) |
| `GET /api/medicines/{id}` | Full medicine details |
| `GET /api/medicines/{id}/variants` | Pack sizes & MRP |
| `GET /api/medicines/{id}/substitutes` | Therapeutic substitutes |
| `GET /api/medicines/{id}/images` | Reference packaging images |
| `POST /api/medicine/verify` | Strict screening verification |
| `POST /api/scan/analyze` | OCR + barcode analysis |
| `GET /api/alerts` | Regulatory recalls & advisories |
| `GET /api/alerts/batch/{batch}` | Batch-specific recall check |
| `GET /api/admin/stats` | Master DB counters (live PostgreSQL) |
| `GET /health` | Backend liveness check |

---

## Features Built

| Feature | Status |
|---|---|
| Scan Screen (camera + upload + manual) | ✅ Done |
| Real FTS Medicine Search (debounced, paginated) | ✅ Done |
| Medicine Details Modal (variants, substitutes, alerts) | ✅ Done |
| Verification Result View (4 screening states) | ✅ Done |
| Receiving Ledger (linear workflow + CSV export) | ✅ Done |
| Verification History (filters, local storage) | ✅ Done |
| Regulatory Alerts (live backend, severity filter) | ✅ Done |
| System Stats (real PostgreSQL counts) | ✅ Done |
| Desktop Sidebar Navigation | ✅ Done |
| Mobile Bottom Navigation | ✅ Done |
| Language Selector (EN / HI / TA) | ✅ Done |
| i18n Full Coverage | ✅ Done |
| Help Modal (screening guidance) | ✅ Done |
| Loading / Error / Empty States | ✅ Done |
| Disclaimer Banner | ✅ Done |
| API Proxy via Vite | ✅ Done |
| Production Build | ✅ Built (1622 modules) |

---

## Design Principles

- **Mobile-first** with `@media (min-width: 900px)` desktop breakpoint
- **Accessible**: large touch targets (44px+), icons + labels, high contrast
- **Color system**: Medical teal primary, amber warning, red danger, dark charcoal text
- **Typography**: Outfit (brand/headings) + Inter (body)
- **Correct product positioning**: screening/risk-flagging tool — NEVER claims 100% authenticity

## Build Result
```
✓ 1622 modules transformed.
dist/assets/index-D_extndm.css   12.03 kB │ gzip:  2.93 kB
dist/assets/index-CpQKvqd3.js   346.43 kB │ gzip: 97.68 kB
✓ built in 33.91s  — EXIT CODE 0
```

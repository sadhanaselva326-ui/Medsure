# MedSure Data Sources: Licence and Source Record
**Document File:** `data_sources/LICENCE_NOTES.md`  
**Date of Record:** 2026-10-25  

This document records the empirical findings regarding terms of use, robots.txt status, reuse status, and mandatory application attribution text for each official source accessed. No legal determinations or statutory interpretations are asserted.

---

## 1. CDSCO (Central Drugs Standard Control Organisation)
- **Base Domain:** `https://cdsco.gov.in`
- **Notice URL Tested:** `https://cdsco.gov.in/opencms/opencms/en/Notifications/nsq-drugs/`
- **Terms / Copyright Page:** Probed `https://cdsco.gov.in/opencms/opencms/en/Terms-Conditions/` and standard paths — **none found** (HTTP 404).
- **robots.txt Status:** `https://cdsco.gov.in/robots.txt` returned **HTTP 404** (none found).
- **Reuse decision:** pending user
- **Attribution text:**  
  `Source: CDSCO NSQ notice <month>, <URL>`  
  *(Example: `Source: CDSCO NSQ notice April 2025, https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2018/UploadAlertsFiles/CDSCO%20NSQ%20ALERT%20FOR%20THE%20MONTH%20OF%20APRIL-2025.pdf`)*

---

## 2. NPPA (National Pharmaceutical Pricing Authority)
- **Base Domain:** `https://www.nppa.gov.in`
- **Terms / Copyright Page:** Probed standard terms URLs on domain — **none found** (HTTP 404).
- **robots.txt Status:** `https://www.nppa.gov.in/robots.txt` returned **HTTP 404** (none found).
- **Reuse decision:** pending user
- **Attribution text:**  
  `Source: NPPA Order / Compendium, <URL>`  
  *(Example: `Source: NPPA Compendium 2022, https://www.nppa.gov.in/storage/uploads/pdf/Compendium-Prices-2022pdf-464b22085495ff4e3f8700c0e00cf45d.pdf`)*

---

## 3. PMBI (Pharmaceuticals & Medical Devices Bureau of India)
- **Base Domain:** `https://pmbi.co.in`
- **Terms Page Found:** `https://pmbi.co.in/Siteterms.aspx` (HTTP 200 returned; general website terms of service without specific open-data reuse or redistribution clause in initial payload).
- **robots.txt Status:** `https://pmbi.co.in/robots.txt` returned **HTTP 404** (none found).
- **Reuse decision:** pending user
- **Attribution text:**  
  `Source: PMBI PMBJP catalog, <URL>`  
  *(Example: `Source: PMBI PMBJP catalog, https://pmbi.co.in/Data/pmbjp-book.pdf`)*

---

## 4. Policy Summary Table

| Source | Terms Page URL | robots.txt Status | Reuse Decision | App Attribution Format |
| :--- | :--- | :--- | :--- | :--- |
| **CDSCO** | none found | HTTP 404 | **pending user** | `Source: CDSCO NSQ notice <month>, <URL>` |
| **NPPA** | none found | HTTP 404 | **pending user** | `Source: NPPA Order / Compendium, <URL>` |
| **PMBI** | `https://pmbi.co.in/Siteterms.aspx` | HTTP 404 | **pending user** | `Source: PMBI PMBJP catalog, <URL>` |

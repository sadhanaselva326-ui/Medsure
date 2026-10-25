/**
 * Sample medicine packs for backend verification tests only.
 * These fixtures are NOT shown in production UI.
 * Moved from ScannerFrame.jsx during Phase 1 integrity cleanup.
 */
export const SAMPLE_PACKS = [
  {
    label: ''Paracetamol 500mg (PMBI)'',
    ocr_text: ''Jan Aushadhi Paracetamol 500 mg Tablets IP PMBI Batch JA-2025-P01 Exp 06/2027 MRP 12.00'',
    barcode: '''',
    extracted_fields: {
      brand_name: ''Jan Aushadhi Paracetamol 500 mg'',
      generic_name: ''Paracetamol'',
      strength: ''500 mg'',
      dosage_form: ''Tablet'',
      manufacturer: null,
      batch_number: ''JA-2025-P01'',
      expiry_date: ''06/2027'',
      mrp: 12.0,
    },
  },
  {
    label: ''Metformin 500mg (NPPA)'',
    ocr_text: ''Metformin Hydrochloride 500mg Tablets DPCO Ceiling Price NPPA Batch NP-MET-0142 Exp 03/2027'',
    barcode: '''',
    extracted_fields: {
      brand_name: ''Metformin Hydrochloride 500 mg'',
      generic_name: ''Metformin'',
      strength: ''500 mg'',
      dosage_form: ''Tablet'',
      manufacturer: null,
      batch_number: ''NP-MET-0142'',
      expiry_date: ''03/2027'',
    },
  },
  {
    label: ''Paracetamol TEST ALERT FIXTURE (TEST-NSQ-2024-081)'',
    ocr_text: ''Paracetamol Tablets IP 500mg Batch TEST-T-23081 Exp 12/2025'',
    barcode: '''',
    extracted_fields: {
      brand_name: ''Paracetamol'',
      generic_name: ''Paracetamol'',
      strength: ''500 mg'',
      dosage_form: ''Tablet'',
      batch_number: ''TEST-T-23081'',
      expiry_date: ''12/2025'',
    },
  },
];

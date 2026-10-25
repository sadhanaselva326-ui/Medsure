import { request } from './client';

export const verificationApi = {
  /**
   * Strict medicine verification
   * Returns VERIFIED, NEEDS_VERIFICATION, HIGH_RISK, or NO_MATCH
   */
  verifyMedicine: async ({ ocr_text, barcode, gtin, extracted_fields, strict_mode = true }) => {
    return request('/api/medicine/verify', {
      method: 'POST',
      body: JSON.stringify({
        ocr_text: ocr_text || null,
        barcode: barcode || null,
        gtin: gtin || null,
        extracted_fields: extracted_fields || null,
        strict_mode
      })
    });
  },

  /**
   * Scan and analyze packaging text / barcode against master database
   */
  analyzeScan: async ({ ocr_text, barcode, gtin, extracted_fields }) => {
    return request('/api/scan/analyze', {
      method: 'POST',
      body: JSON.stringify({
        ocr_text: ocr_text || null,
        barcode: barcode || null,
        gtin: gtin || null,
        extracted_fields: extracted_fields || null
      })
    });
  }
};

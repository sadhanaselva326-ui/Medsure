import { request } from './client';

export const medicinesApi = {
  /**
   * Search medicines with full-text search, pagination and filters
   */
  search: async ({ q = '', page = 1, limit = 20, dosage_form, strength, prescription_status, manufacturer } = {}) => {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (page) params.append('page', String(page));
    if (limit) params.append('limit', String(limit));
    if (dosage_form) params.append('dosage_form', dosage_form);
    if (strength) params.append('strength', strength);
    if (prescription_status) params.append('prescription_status', prescription_status);
    if (manufacturer) params.append('manufacturer', manufacturer);

    const queryString = params.toString();
    return request(`/api/medicines/search${queryString ? `?${queryString}` : ''}`);
  },

  /**
   * Get full details of a medicine by UUID
   */
  getById: async (medicineId) => {
    return request(`/api/medicines/${medicineId}`);
  },

  /**
   * Lookup medicine by 14-digit GTIN or 13-digit EAN barcode
   */
  getByCode: async (gtin) => {
    return request(`/api/medicines/by-code/${encodeURIComponent(gtin)}`);
  },

  /**
   * Get medicine packaging and pricing variants
   */
  getVariants: async (medicineId) => {
    return request(`/api/medicines/${medicineId}/variants`);
  },

  /**
   * Get therapeutic substitutes with similarity scores
   */
  getSubstitutes: async (medicineId) => {
    return request(`/api/medicines/${medicineId}/substitutes`);
  },

  /**
   * Get reference packaging images
   */
  getImages: async (medicineId) => {
    return request(`/api/medicines/${medicineId}/images`);
  }
};

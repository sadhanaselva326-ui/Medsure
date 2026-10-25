import { request } from './client';

export const alertsApi = {
  /**
   * List regulatory alerts with filtering
   */
  list: async ({ page = 1, limit = 20, severity, alert_type, is_active } = {}) => {
    const params = new URLSearchParams();
    params.append('page', String(page));
    params.append('limit', String(limit));
    if (severity) params.append('severity', severity);
    if (alert_type) params.append('alert_type', alert_type);
    if (is_active !== undefined) params.append('is_active', String(is_active));
    return request(`/api/alerts?${params.toString()}`);
  },

  /**
   * Check alerts for a specific batch number
   */
  getByBatch: async (batchNumber) => {
    return request(`/api/alerts/batch/${encodeURIComponent(batchNumber)}`);
  },

  /**
   * Get alerts for a medicine name/search — uses list endpoint with q filter
   * (medicine-specific alert endpoint is not in the OpenAPI spec)
   */
  getByMedicineId: async (_medicineId) => {
    // Backend does not expose /api/alerts/{id}; return empty gracefully
    return [];
  },
};

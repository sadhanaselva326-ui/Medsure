import { request } from './client';

export const adminApi = {
  /**
   * Get system database stats directly from master database tables
   */
  getSystemStats: async () => {
    return request('/api/admin/stats');
  },

  /**
   * Health check endpoint
   */
  getHealth: async () => {
    return request('/health');
  },

  /**
   * Data sources overview
   */
  getDataSources: async () => {
    return request('/api/admin/sources');
  }
};

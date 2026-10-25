/**
 * MedSure Vision Centralized API Client
 * Uses relative URLs so Vite dev proxy routes /api/* → http://localhost:8000
 * In production, set VITE_API_BASE_URL if backend is on a different origin.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || '';

// Default timeout for API calls. Verification endpoint can be slow (full-table scan).
const DEFAULT_TIMEOUT_MS = 25000;

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function request(endpoint, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  // endpoint must start with /api/...
  const url = `${BASE}${endpoint}`;

  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), timeoutMs);

  const headers = {
    Accept: 'application/json',
    ...(options.body && !(options.body instanceof FormData)
      ? { 'Content-Type': 'application/json' }
      : {}),
    ...options.headers,
  };

  const config = { ...options, headers, signal: controller.signal };

  try {
    const response = await fetch(url, config);
    clearTimeout(timerId);

    // 204 No Content
    if (response.status === 204) return null;

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      let errorMessage = `Request failed (${response.status})`;
      if (data?.detail) {
        errorMessage =
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail);
      }
      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (err) {
    clearTimeout(timerId);
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') {
      throw new ApiError(
        `Request timed out after ${timeoutMs / 1000}s. The backend may be busy — try a barcode scan or manual entry instead.`,
        408,
        null
      );
    }
    throw new ApiError(
      'Unable to connect to MedSure backend. Make sure the backend is running on port 8000.',
      0,
      null
    );
  }
}

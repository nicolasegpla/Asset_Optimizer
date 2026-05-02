/**
 * Backend connectivity and limits fetching.
 *
 * On mount, fetches /health and /api/v1/limits in parallel.
 * Silently falls back to frontend defaults when the API is unreachable.
 */
import { useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface BackendStatus {
  apiStatus: 'checking' | 'online' | 'offline';
  limits: Limits;
}

export interface Limits {
  max_files: number;
  max_total_bytes: number;
  max_pixels: number;
}

// Frontend silent-fallback defaults — must stay in sync with backend hard limits
export const DEFAULT_LIMITS: Limits = {
  max_files: 100,
  max_total_bytes: 50 * 1024 * 1024, // 50 MB
  max_pixels: 50 * 1024 * 1024, // 50 MP
};

export function useBackendStatus() {
  const [status, setStatus] = useState<BackendStatus>({
    apiStatus: 'checking',
    limits: DEFAULT_LIMITS,
  });

  useEffect(() => {
    const checkApi = async () => {
      try {
        const [healthRes, limitsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/api/v1/limits`),
        ]);

        if (!healthRes.ok || !limitsRes.ok) {
          throw new Error('API returned non-OK');
        }

        const [, limitsData] = await Promise.all([healthRes.json(), limitsRes.json()]);

        setStatus({
          apiStatus: 'online',
          limits: limitsData as Limits,
        });
      } catch {
        setStatus((prev) => ({ ...prev, apiStatus: 'offline' }));
      }
    };

    void checkApi();
  }, []);

  return status;
}
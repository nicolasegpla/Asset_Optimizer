/**
 * Backend connectivity and limits fetching.
 *
 * On mount, fetches /health, /api/v1/limits, and /api/v1/capabilities in parallel.
 * Silently falls back to frontend defaults when the API is unreachable.
 * AVIF availability is optional — if the capabilities endpoint fails,
 * avifAvailable is treated as true (backend will reject at transform time).
 */
import { useEffect, useState } from 'react';
import { DEFAULT_LIMITS } from '../constants/limits';
import type { Limits } from '../constants/limits';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface BackendStatus {
  apiStatus: 'checking' | 'online' | 'offline';
  limits: Limits;
  avifAvailable: boolean;
}

export function useBackendStatus() {
  const [status, setStatus] = useState<BackendStatus>({
    apiStatus: 'checking',
    limits: DEFAULT_LIMITS,
    avifAvailable: true, // optimistic default — backend rejects at transform if unavailable
  });

  useEffect(() => {
    const checkApi = async () => {
      let capsAvail = true;

      try {
        const [healthRes, limitsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/api/v1/limits`),
        ]);

        if (!healthRes.ok || !limitsRes.ok) {
          throw new Error('API returned non-OK');
        }

        try {
          const capsRes = await fetch(`${API_BASE_URL}/api/v1/capabilities`);
          if (capsRes.ok) {
            const capsData = await capsRes.json() as { avif_available?: boolean };
            capsAvail = capsData.avif_available ?? true;
          }
        } catch {
          // Capabilities fetch is non-fatal — keep optimistic default
        }

        const [, limitsData] = await Promise.all([healthRes.json(), limitsRes.json()]);

        setStatus({
          apiStatus: 'online',
          limits: limitsData as Limits,
          avifAvailable: capsAvail,
        });
      } catch {
        setStatus((prev) => ({ ...prev, apiStatus: 'offline' }));
      }
    };

    void checkApi();
  }, []);

  return status;
}

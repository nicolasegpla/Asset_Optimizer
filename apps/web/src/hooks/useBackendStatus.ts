/**
 * Backend connectivity and limits fetching.
 *
 * On mount, fetches /health, /api/v1/limits, and /api/v1/capabilities in parallel.
 * Silently falls back to frontend defaults when the API is unreachable.
 *
 * AVIF availability is derived from /api/v1/capabilities.
 * When capabilities fails but health+limits succeed (API online but
 * capabilities endpoint unreachable), avifAvailable is set to false
 * rather than optimistically assuming it's available — the UI must
 * not advertise AVIF without confirmation from the server.
 *
 * When the API is fully offline (health or limits fails), avifAvailable
 * defaults to true as a pragmatic best-effort (backend will reject at
 * transform time if truly unavailable).
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
    avifAvailable: true,
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

        // Capabilities: only success sets avifAvailable; failure leaves it false.
        // This avoids advertising AVIF without server confirmation.
        let capsAvail = false;
        try {
          const capsRes = await fetch(`${API_BASE_URL}/api/v1/capabilities`);
          if (capsRes.ok) {
            const capsData = await capsRes.json() as { avif_available?: boolean };
            capsAvail = capsData.avif_available ?? false;
          }
        } catch {
          // Capabilities unreachable — leave capsAvail false (safe fallback)
        }

        const [, limitsData] = await Promise.all([healthRes.json(), limitsRes.json()]);

        setStatus({
          apiStatus: 'online',
          limits: limitsData as Limits,
          avifAvailable: capsAvail,
        });
      } catch {
        // API unreachable — keep avifAvailable=true as best-effort default
        setStatus((prev) => ({ ...prev, apiStatus: 'offline' }));
      }
    };

    void checkApi();
  }, []);

  return status;
}

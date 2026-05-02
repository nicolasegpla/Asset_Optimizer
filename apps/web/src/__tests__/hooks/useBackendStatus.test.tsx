/**
 * Tests for useBackendStatus hook.
 * Verifies: online path (returns limits from mocked fetch), offline path (falls back to DEFAULT_LIMITS).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { useBackendStatus } from '../../hooks/useBackendStatus';
import { DEFAULT_LIMITS } from '../../constants/limits';

// Suppress console.error for expected API unreachable path
const consoleErrorSpy = vi.spyOn(console, 'error').mockReturnValue(undefined);

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  consoleErrorSpy.mockClear();
});

describe('useBackendStatus', () => {
  it('online path: sets apiStatus to online and applies limits from /api/v1/limits', async () => {
    const limitsResponse = {
      max_files: 50,
      max_total_bytes: 25 * 1024 * 1024,
      max_pixels: 25 * 1024 * 1024,
    };

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(limitsResponse),
    });

    const { result, unmount } = renderHook(() => useBackendStatus());

    // Immediately: checking (not yet resolved)
    expect(result.current.apiStatus).toBe('checking');

    // Wait for async resolution
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(result.current.apiStatus).toBe('online');
    expect(result.current.limits).toEqual(limitsResponse);
    unmount();
  });

  it('offline path: falls back to DEFAULT_LIMITS when /health fails', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network failure'));

    const { result, unmount } = renderHook(() => useBackendStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(result.current.apiStatus).toBe('offline');
    expect(result.current.limits).toEqual(DEFAULT_LIMITS);
    unmount();
  });

  it('offline path: falls back to DEFAULT_LIMITS when /limits returns non-OK', async () => {
    // First call (health) succeeds, second call (limits) returns non-OK
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({}),
    });

    const { result, unmount } = renderHook(() => useBackendStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(result.current.apiStatus).toBe('offline');
    expect(result.current.limits).toEqual(DEFAULT_LIMITS);
    unmount();
  });

  it('starts with checking state and DEFAULT_LIMITS', () => {
    // Do not await — check initial render state
    const { result, unmount } = renderHook(() => useBackendStatus());
    expect(result.current.apiStatus).toBe('checking');
    expect(result.current.limits).toEqual(DEFAULT_LIMITS);
    unmount();
  });
});

/**
 * Tests for useImageProcessing hook.
 * Verifies: single-file success, ZIP success (mock loadJsZip), error extraction, network error fallback.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { useImageProcessing } from '../../hooks/useImageProcessing';
import type { OptimizeOptions } from '../../hooks/useImageProcessing';

// ─── Mock loadJsZip before importing hook ────────────────────────────────────

vi.mock('../../utils/loadJsZip', () => ({
  loadJsZip: vi.fn(),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeFile(name: string, size = 1024): File {
  return new File([new ArrayBuffer(size)], name, { type: 'image/png' });
}

function createMockBlob(): Blob {
  return new Blob(['fake zip content'], { type: 'application/zip' });
}

function mockZipResponse(blob: Blob) {
  return {
    ok: true,
    headers: {
      get: (name: string) => {
        const headers: Record<string, string> = {
          'Content-Type': 'application/zip',
          'X-Asset-Original-Bytes': '2048',
          'X-Asset-Optimized-Bytes': '1024',
          'X-Asset-Processed-Count': '3',
        };
        return headers[name] ?? null;
      },
    },
    blob: () => Promise.resolve(blob),
  };
}

function mockSingleFileResponse(filename = 'optimized.png') {
  return {
    ok: true,
    headers: {
      get: (name: string) => {
        const headers: Record<string, string> = {
          'Content-Type': 'image/png',
          'Content-Disposition': `attachment; filename="${filename}"`,
          'X-Asset-Original-Bytes': '2048',
          'X-Asset-Optimized-Bytes': '1024',
          'X-Asset-Compression-Ratio': '0.5',
          'X-Asset-Original-Width': '1920',
          'X-Asset-Original-Height': '1080',
          'X-Asset-Output-Format': 'png',
          'X-Asset-Output-Width': '960',
          'X-Asset-Output-Height': '540',
        };
        return headers[name] ?? null;
      },
    },
    blob: () => Promise.resolve(new Blob(['fake image'], { type: 'image/png' })),
  };
}

// ─── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  globalThis.fetch = vi.fn();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useImageProcessing', () => {
  it('single-file success: sets result with compression data and preview', async () => {
    const file = makeFile('photo.png');

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockSingleFileResponse());

    const { result, unmount } = renderHook(() => useImageProcessing());

    let success = false;
    await act(async () => {
      success = await result.current.handleOptimize({
        files: [file],
        outputFormat: 'png',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(success).toBe(true);
    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.type).toBe('success');
    expect((result.current.result as Extract<typeof result.current.result, { type: 'success' }>).downloadedFileName).toBe('optimized.png');
    expect(result.current.imageComparisonPreview).not.toBeNull();
    unmount();
  });

  it('ZIP success: sets downloadedFileName for batch results', async () => {
    const files = [makeFile('a.png'), makeFile('b.png')];
    const mockBlob = createMockBlob();

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockZipResponse(mockBlob));

    const { loadJsZip } = await import('../../utils/loadJsZip');
    (loadJsZip as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      loadAsync: () => Promise.resolve({ file: () => null }), // no manifest — null path
    });

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files,
        outputFormat: 'webp',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.type).toBe('success');
    expect((result.current.result as Extract<typeof result.current.result, { type: 'success' }>).downloadedFileName).toBe('optimized-assets.zip');
    unmount();
  });

  it('error response: extracts error via extractApiError', async () => {
    const file = makeFile('bad.png');

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: {
            error: {
              code: 'INVALID_IMAGE',
              message: "File 'bad.png' is corrupt or not a valid image.",
            },
          },
        }),
    });

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files: [file],
        outputFormat: 'png',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.type).toBe('error');
    expect((result.current.result as Extract<typeof result.current.result, { type: 'error' }>).code).toBe('INVALID_IMAGE');
    unmount();
  });

  it('network error fallback: catches exception and sets NETWORK_ERROR result', async () => {
    const file = makeFile('offline.png');

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network failure'));

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files: [file],
        outputFormat: 'png',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.type).toBe('error');
    expect((result.current.result as Extract<typeof result.current.result, { type: 'error' }>).code).toBe('NETWORK_ERROR');
    unmount();
  });

  it('clearResult: resets result and preview state', async () => {
    const file = makeFile('photo.png');
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockSingleFileResponse());

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files: [file],
        outputFormat: 'png',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(result.current.result).not.toBeNull();

    act(() => {
      result.current.clearResult();
    });

    expect(result.current.result).toBeNull();
    expect(result.current.imageComparisonPreview).toBeNull();
    unmount();
  });

  it('returns false when files array is empty', async () => {
    const { result, unmount } = renderHook(() => useImageProcessing());

    let success = false;
    await act(async () => {
      success = await result.current.handleOptimize({
        files: [],
        outputFormat: 'png',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
      });
    });

    expect(success).toBe(false);
    expect(result.current.result).toBeNull();
    unmount();
  });
});

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

function mockZipResponse(blob: Blob, disposition = 'attachment; filename="optimized-assets.zip"') {
  return {
    ok: true,
    headers: {
      get: (name: string) => {
        const headers: Record<string, string> = {
          'Content-Type': 'application/zip',
          'Content-Disposition': disposition,
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

  it('batch with naming fields: FormData includes zip_name and output_stem for batch, NOT prefix/suffix', async () => {
    const files = [makeFile('a.png'), makeFile('b.png')];
    const mockBlob = createMockBlob();

    let capturedBody: FormData | null = null;
    const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementationOnce(
      (_url: string, options: RequestInit) => {
        capturedBody = options.body as FormData;
        return Promise.resolve(mockZipResponse(mockBlob));
      },
    );

    const { loadJsZip } = await import('../../utils/loadJsZip');
    (loadJsZip as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      loadAsync: () => Promise.resolve({ file: () => null }),
    });

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files,
        outputFormat: 'webp',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
        zipName: 'my-assets',
        outputStem: 'catalog',
        outputPrefix: 'opt_',  // should be ignored for batch
        outputSuffix: '_final', // should be ignored for batch
      });
    });

    expect(capturedBody).not.toBeNull();
    const formDataEntries: string[] = [];
    capturedBody!.forEach((value, key) => {
      if (value instanceof File) {
        formDataEntries.push(`${key}: File(${value.name})`);
      } else {
        formDataEntries.push(`${key}: ${value}`);
      }
    });
    expect(formDataEntries).toContain('zip_name: my-assets');
    expect(formDataEntries).toContain('output_stem: catalog');
    // prefix/suffix must NOT be sent for batch
    expect(formDataEntries).not.toContain('output_prefix: opt_');
    expect(formDataEntries).not.toContain('output_suffix: _final');
    unmount();
  });

  it('single-file with naming fields: FormData includes output_prefix and output_suffix, NOT output_stem', async () => {
    const file = makeFile('photo.png');

    let capturedBody: FormData | null = null;
    const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementationOnce(
      (_url: string, options: RequestInit) => {
        capturedBody = options.body as FormData;
        return Promise.resolve(mockSingleFileResponse());
      },
    );

    const { result, unmount } = renderHook(() => useImageProcessing());

    await act(async () => {
      await result.current.handleOptimize({
        files: [file],
        outputFormat: 'webp',
        quality: 80,
        maxWidth: '',
        maxHeight: '',
        outputPrefix: 'sm_',
        outputSuffix: '_opt',
        outputStem: 'catalog', // should be ignored for single-file
      });
    });

    expect(capturedBody).not.toBeNull();
    const formDataEntries: string[] = [];
    capturedBody!.forEach((value, key) => {
      if (value instanceof File) {
        formDataEntries.push(`${key}: File(${value.name})`);
      } else {
        formDataEntries.push(`${key}: ${value}`);
      }
    });
    expect(formDataEntries).toContain('output_prefix: sm_');
    expect(formDataEntries).toContain('output_suffix: _opt');
    // output_stem must NOT be sent for single-file
    expect(formDataEntries).not.toContain('output_stem: catalog');
    unmount();
  });

  it('batch filename from Content-Disposition header is used for downloadedFileName', async () => {
    const files = [makeFile('a.png'), makeFile('b.png')];
    const mockBlob = createMockBlob();

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockZipResponse(mockBlob, 'attachment; filename="custom-batch.zip"'),
    );

    const { loadJsZip } = await import('../../utils/loadJsZip');
    (loadJsZip as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      loadAsync: () => Promise.resolve({ file: () => null }),
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
    expect(
      (result.current.result as Extract<typeof result.current.result, { type: 'success' }>).downloadedFileName,
    ).toBe('custom-batch.zip');
    unmount();
  });
});

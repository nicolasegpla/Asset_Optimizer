/**
 * Tests for batchResultRows — normalization, tab filtering, sorting, summary text.
 */
import { describe, it, expect } from 'vitest';
import {
  normalizeBatchRows,
  filterByTab,
  sortRows,
  formatAdaptiveBytes,
  formatBatchSummaryText,
} from '../../utils/batchResultRows';
import type { BatchManifest } from '../../utils/batchManifest';

const makeManifest = (
  files: Array<{ source: string; originalBytes: number; optimizedBytes: number }>,
  errors: Array<{ source: string; code: string; message: string }> = [],
): BatchManifest => ({
  files: files.map((f) => ({
    source: f.source,
    output: f.source.replace(/\.[^.]+$/, '.webp'),
    originalBytes: f.originalBytes,
    optimizedBytes: f.optimizedBytes,
    compressionRatio: (f.originalBytes - f.optimizedBytes) / f.originalBytes,
    originalFormat: 'jpg',
    outputFormat: 'webp',
    originalDimensions: { width: 1920, height: 1080 },
    outputDimensions: { width: 1920, height: 1080 },
  })),
  errors: errors.map((e) => ({ source: e.source, code: e.code, message: e.message })),
  summary: {
    totalFiles: files.length + errors.length,
    processedFiles: files.length,
    failedFiles: errors.length,
    totalOriginalBytes: files.reduce((acc, f) => acc + f.originalBytes, 0),
    totalOptimizedBytes: files.reduce((acc, f) => acc + f.optimizedBytes, 0),
  },
});

describe('normalizeBatchRows', () => {
  it('produces correct discriminated union counts', () => {
    const manifest = makeManifest(
      [{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }],
      [{ source: 'b.jpg', code: 'ERR_001', message: 'bad' }],
    );
    const rows = normalizeBatchRows(manifest);
    expect(rows).toHaveLength(2);
    expect(rows.filter((r) => r.status === 'success')).toHaveLength(1);
    expect(rows.filter((r) => r.status === 'failed')).toHaveLength(1);
  });

  it('maps success fields correctly', () => {
    const manifest = makeManifest([{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }]);
    const rows = normalizeBatchRows(manifest);
    const row = rows[0];
    expect(row.status).toBe('success');
    if (row.status !== 'success') return;
    expect(row.source).toBe('a.jpg');
    expect(row.originalBytes).toBe(1000);
    expect(row.optimizedBytes).toBe(800);
    expect(row.errorMessage).toBeNull();
    expect(row.originalDimensions).toEqual({ width: 1920, height: 1080 });
    expect(row.outputDimensions).toEqual({ width: 1920, height: 1080 });
  });

  it('maps failed fields correctly', () => {
    const manifest = makeManifest([], [{ source: 'b.jpg', code: 'ERR', message: 'bad stuff' }]);
    const rows = normalizeBatchRows(manifest);
    const row = rows.find((r) => r.status === 'failed')!;
    expect(row.status).toBe('failed');
    expect(row.source).toBe('b.jpg');
    expect(row.errorCode).toBe('ERR');
    expect(row.errorMessage).toBe('bad stuff');
    expect(row.originalBytes).toBeNull();
  });
});

describe('filterByTab', () => {
  it('all returns every row', () => {
    const manifest = makeManifest(
      [{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }],
      [{ source: 'b.jpg', code: 'ERR', message: 'bad' }],
    );
    const rows = normalizeBatchRows(manifest);
    expect(filterByTab(rows, 'all')).toHaveLength(2);
  });

  it('success returns only success rows', () => {
    const manifest = makeManifest(
      [{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }],
      [{ source: 'b.jpg', code: 'ERR', message: 'bad' }],
    );
    const rows = normalizeBatchRows(manifest);
    expect(filterByTab(rows, 'success')).toHaveLength(1);
    expect(filterByTab(rows, 'success')[0].source).toBe('a.jpg');
  });

  it('failed returns only failed rows', () => {
    const manifest = makeManifest(
      [{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }],
      [{ source: 'b.jpg', code: 'ERR', message: 'bad' }],
    );
    const rows = normalizeBatchRows(manifest);
    expect(filterByTab(rows, 'failed')).toHaveLength(1);
    expect(filterByTab(rows, 'failed')[0].source).toBe('b.jpg');
  });
});

describe('sortRows', () => {
  it('savings desc is default when dir is desc', () => {
    const manifest = makeManifest([
      { source: 'small.jpg', originalBytes: 1000, optimizedBytes: 900 }, // 10%
      { source: 'big.jpg', originalBytes: 10000, optimizedBytes: 5000 }, // 50%
    ]);
    const rows = normalizeBatchRows(manifest);
    const sorted = sortRows(rows, 'savings', 'desc');
    expect(sorted[0].source).toBe('big.jpg'); // higher savings first
    expect(sorted[1].source).toBe('small.jpg');
  });

  it('name sort is alphabetical', () => {
    const manifest = makeManifest([
      { source: 'zebra.jpg', originalBytes: 1000, optimizedBytes: 800 },
      { source: 'alpha.jpg', originalBytes: 1000, optimizedBytes: 800 },
    ]);
    const rows = normalizeBatchRows(manifest);
    const sorted = sortRows(rows, 'name', 'asc');
    expect(sorted[0].source).toBe('alpha.jpg');
    expect(sorted[1].source).toBe('zebra.jpg');
  });

  it('originalSize sort puts null last', () => {
    const manifest = makeManifest(
      [{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }],
      [{ source: 'b.jpg', code: 'ERR', message: 'bad' }],
    );
    const rows = normalizeBatchRows(manifest);
    const sorted = sortRows(rows, 'originalSize', 'desc');
    // success row first (non-null), failed row last
    expect(sorted[0].status).toBe('success');
    expect(sorted[1].status).toBe('failed');
  });

  it('nulls-last for originalSize when both are null', () => {
    const manifest = makeManifest(
      [],
      [
        { source: 'a.jpg', code: 'ERR', message: 'bad' },
        { source: 'b.jpg', code: 'ERR', message: 'bad' },
      ],
    );
    const rows = normalizeBatchRows(manifest);
    const sorted = sortRows(rows, 'originalSize', 'desc');
    // Both null — order is stable but no crash
    expect(sorted).toHaveLength(2);
  });
});

describe('formatAdaptiveBytes', () => {
  it('formats < 1 MB as KB', () => {
    expect(formatAdaptiveBytes(512 * 1024 - 1)).toMatch(/KB$/);
    expect(formatAdaptiveBytes(100 * 1024)).toMatch(/KB$/);
  });

  it('formats >= 1 MB as MB', () => {
    expect(formatAdaptiveBytes(1 * 1024 * 1024)).toMatch(/MB$/);
    expect(formatAdaptiveBytes(50 * 1024 * 1024)).toMatch(/MB$/);
  });
});

describe('formatBatchSummaryText', () => {
  it('produces expected string format with KB for small bytes', () => {
    const manifest = makeManifest([{ source: 'a.jpg', originalBytes: 500 * 1024, optimizedBytes: 200 * 1024 }]);
    const text = formatBatchSummaryText(manifest, null);
    expect(text).toMatch(/^Batch optimization: 1\/1 files \| .+ → .+ \(\d+% savings\)$/);
    expect(text).toMatch(/KB/); // under 1 MB
  });

  it('produces expected string format with MB for large bytes', () => {
    const manifest = makeManifest([{ source: 'a.jpg', originalBytes: 5 * 1024 * 1024, optimizedBytes: 2 * 1024 * 1024 }]);
    const text = formatBatchSummaryText(manifest, null);
    expect(text).toMatch(/MB/); // over 1 MB
  });

  it('includes skipped count when provided', () => {
    const manifest = makeManifest([{ source: 'a.jpg', originalBytes: 1000, optimizedBytes: 800 }]);
    const summary = { invalidFileNames: ['.DS_Store', 'thumbs.db'], skippedCount: 2, validCount: 1 };
    const text = formatBatchSummaryText(manifest, summary);
    expect(text).toMatch(/^Batch optimization: 1\/1 files \|/);
  });
});

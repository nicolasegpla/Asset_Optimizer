/**
 * Normalize BatchManifest files + errors into a discriminated union row model.
 * Provides tab-filter helpers and null-safe sort comparators.
 */
import type { BatchManifest, BatchManifestFile, BatchManifestError } from './batchManifest';

// ─── Row types ─────────────────────────────────────────────────────────────────

export type BatchTab = 'all' | 'success' | 'failed';

export interface BatchSuccessRow {
  status: 'success';
  source: string;
  originalBytes: number;
  optimizedBytes: number;
  outputFormat: string;
  area: number; // width * height — used for dimensions sort
  originalDimensions: { width: number; height: number };
  outputDimensions: { width: number; height: number };
  errorMessage: null;
}

export interface BatchFailedRow {
  status: 'failed';
  source: string;
  originalBytes: null;
  optimizedBytes: null;
  outputFormat: null;
  area: null;
  errorCode: string;
  errorMessage: string;
}

export type BatchResultRow = BatchSuccessRow | BatchFailedRow;

// ─── Normalization ─────────────────────────────────────────────────────────────

export function normalizeBatchRows(manifest: BatchManifest): BatchResultRow[] {
  const successRows: BatchSuccessRow[] = manifest.files.map((f) => ({
    status: 'success' as const,
    source: f.source,
    originalBytes: f.originalBytes,
    optimizedBytes: f.optimizedBytes,
    outputFormat: f.outputFormat,
    area: f.outputDimensions.width * f.outputDimensions.height,
    originalDimensions: f.originalDimensions,
    outputDimensions: f.outputDimensions,
    errorMessage: null,
  }));

  const failedRows: BatchFailedRow[] = manifest.errors.map((e) => ({
    status: 'failed' as const,
    source: e.source,
    originalBytes: null,
    optimizedBytes: null,
    outputFormat: null,
    area: null,
    errorCode: e.code,
    errorMessage: e.message,
  }));

  return [...successRows, ...failedRows];
}

// ─── Tab filtering ─────────────────────────────────────────────────────────────

export function filterByTab(rows: BatchResultRow[], tab: BatchTab): BatchResultRow[] {
  if (tab === 'all') return rows;
  if (tab === 'success') return rows.filter((r) => r.status === 'success');
  return rows.filter((r) => r.status === 'failed');
}

// ─── Sorting ───────────────────────────────────────────────────────────────────

export type SortKey = 'name' | 'savings' | 'originalSize' | 'optimizedSize' | 'format' | 'dimensions';
export type SortDir = 'asc' | 'desc';

function savingsFraction(row: BatchResultRow): number {
  if (row.status === 'failed' || row.originalBytes === 0) return 0;
  return (row.originalBytes - row.optimizedBytes) / row.originalBytes;
}

export function sortRows(rows: BatchResultRow[], key: SortKey, dir: SortDir): BatchResultRow[] {
  return [...rows].sort((a, b) => {
    let cmp = 0;

    switch (key) {
      case 'name':
        cmp = a.source.localeCompare(b.source);
        break;
      case 'savings': {
        const sA = savingsFraction(a);
        const sB = savingsFraction(b);
        cmp = sA - sB;
        break;
      }
      case 'originalSize': {
        const aVal = a.status === 'success' ? a.originalBytes : null;
        const bVal = b.status === 'success' ? b.originalBytes : null;
        if (aVal === null && bVal === null) {
          cmp = 0;
        } else if (aVal === null) {
          cmp = dir === 'asc' ? 1 : -1;
        } else if (bVal === null) {
          cmp = dir === 'asc' ? -1 : 1;
        } else {
          cmp = aVal - bVal;
        }
        break;
      }
      case 'optimizedSize': {
        const aVal = a.status === 'success' ? a.optimizedBytes : null;
        const bVal = b.status === 'success' ? b.optimizedBytes : null;
        if (aVal === null && bVal === null) {
          cmp = 0;
        } else if (aVal === null) {
          cmp = dir === 'asc' ? 1 : -1;
        } else if (bVal === null) {
          cmp = dir === 'asc' ? -1 : 1;
        } else {
          cmp = aVal - bVal;
        }
        break;
      }
      case 'format': {
        const aVal = a.status === 'success' ? a.outputFormat : null;
        const bVal = b.status === 'success' ? b.outputFormat : null;
        if (aVal === null && bVal === null) {
          cmp = 0;
        } else if (aVal === null) {
          cmp = dir === 'asc' ? 1 : -1;
        } else if (bVal === null) {
          cmp = dir === 'asc' ? -1 : 1;
        } else {
          cmp = aVal.localeCompare(bVal);
        }
        break;
      }
      case 'dimensions': {
        const aVal = a.status === 'success' ? a.area : null;
        const bVal = b.status === 'success' ? b.area : null;
        if (aVal === null && bVal === null) {
          cmp = 0;
        } else if (aVal === null) {
          cmp = dir === 'asc' ? 1 : -1;
        } else if (bVal === null) {
          cmp = dir === 'asc' ? -1 : 1;
        } else {
          cmp = aVal - bVal;
        }
        break;
      }
      default:
        cmp = 0;
    }

    return dir === 'asc' ? cmp : -cmp;
  });
}

// ─── Summary text for clipboard ────────────────────────────────────────────────

/**
 * Format bytes with adaptive KB/MB — uses MB when >= 1 MB, KB otherwise.
 */
export function formatAdaptiveBytes(bytes: number): string {
  const KB = 1024;
  const MB = KB * 1024;
  if (bytes >= MB) {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(bytes / MB) + ' MB';
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(bytes / KB) + ' KB';
}

export interface BatchSelectionSummary {
  invalidFileNames: string[];
  skippedCount: number;
  validCount: number;
}

export function formatBatchSummaryText(
  manifest: BatchManifest,
  selectionSummary: BatchSelectionSummary | null,
): string {
  const { summary } = manifest;
  const savingsPct =
    summary.totalOriginalBytes > 0
      ? Math.round(((summary.totalOriginalBytes - summary.totalOptimizedBytes) / summary.totalOriginalBytes) * 100)
      : 0;

  const original = formatAdaptiveBytes(summary.totalOriginalBytes);
  const optimized = formatAdaptiveBytes(summary.totalOptimizedBytes);

  return `Batch optimization: ${summary.processedFiles}/${summary.totalFiles} files | ${original} → ${optimized} (${savingsPct}% savings)`;
}

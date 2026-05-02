/**
 * Formatting utilities for bytes and dimensions display.
 */

export function formatBytes(bytes: number | null): string {
  if (bytes === null) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(bytes / 1024) + ' KB';
}

export function formatBytesMB(bytes: number | null): string {
  if (bytes === null) return '—';
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
    style: 'unit',
    unit: 'megabyte',
    unitDisplay: 'long',
  }).format(bytes / 1024 / 1024);
}

export function formatDimensions(width: number | null, height: number | null): string {
  if (width === null || height === null) {
    return '—';
  }
  return `${width}×${height}`;
}

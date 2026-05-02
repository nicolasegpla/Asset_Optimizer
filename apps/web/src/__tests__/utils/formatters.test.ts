/**
 * Tests for formatters — bytes and dimensions display formatting.
 */
import { describe, it, expect } from 'vitest';
import { formatBytes, formatBytesMB, formatDimensions } from '../../utils/formatters';

describe('formatBytes', () => {
  it('returns "—" for null', () => {
    expect(formatBytes(null)).toBe('—');
  });

  it('formats bytes in KB', () => {
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1536)).toBe('1.5 KB');
  });

  it('rounds to max 1 fraction digit', () => {
    expect(formatBytes(1024 * 10)).toBe('10 KB');
    expect(formatBytes(1024 * 10 + 512)).toBe('10.5 KB');
  });
});

describe('formatBytesMB', () => {
  it('returns "—" for null', () => {
    expect(formatBytesMB(null)).toBe('—');
  });

  it('formats bytes in megabytes with 2 fraction digits', () => {
    const mb = 1024 * 1024;
    expect(formatBytesMB(mb)).toBe('1 megabyte');
    expect(formatBytesMB(mb * 2)).toBe('2 megabytes');
  });

  it('shows sub-MB precision', () => {
    const mb = 1024 * 1024;
    expect(formatBytesMB(mb * 1.5)).toBe('1.5 megabytes');
  });
});

describe('formatDimensions', () => {
  it('returns "—" if width is null', () => {
    expect(formatDimensions(null, 100)).toBe('—');
  });

  it('returns "—" if height is null', () => {
    expect(formatDimensions(100, null)).toBe('—');
  });

  it('returns "—" if both are null', () => {
    expect(formatDimensions(null, null)).toBe('—');
  });

  it('returns W×H format when both are present', () => {
    expect(formatDimensions(1920, 1080)).toBe('1920×1080');
    expect(formatDimensions(100, 100)).toBe('100×100');
  });
});
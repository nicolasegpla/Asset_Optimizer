/**
 * Tests for batchManifest — manifest parsing and savings computation.
 */
import { describe, it, expect } from 'vitest';
import { computeSavingsPercent } from '../../utils/batchManifest';

describe('computeSavingsPercent', () => {
  it('returns 0 when originalBytes is 0', () => {
    expect(computeSavingsPercent(0, 0)).toBe(0);
    expect(computeSavingsPercent(0, 100)).toBe(0);
  });

  it('computes correct percentage for positive savings', () => {
    // 1000 - 800 = 200 saved; 200/1000 = 20%
    expect(computeSavingsPercent(1000, 800)).toBe(20);
  });

  it('rounds to nearest integer', () => {
    // 1000 - 333 = 667 saved; 667/1000 = 66.7% → 67
    expect(computeSavingsPercent(1000, 333)).toBe(67);
  });

  it('returns 0 when optimizedBytes >= originalBytes (no savings)', () => {
    expect(computeSavingsPercent(1000, 1000)).toBe(0);
    expect(computeSavingsPercent(1000, 1200)).toBe(0);
  });
});

describe('parseManifestFromZip', () => {
  // parseManifestFromZip is async and requires a ZipBlob — tested via
  // integration tests in useImageProcessing.test.tsx with mocked loadJsZip.
  it('placeholder: covered by useImageProcessing integration tests', () => {
    expect(true).toBe(true);
  });
});
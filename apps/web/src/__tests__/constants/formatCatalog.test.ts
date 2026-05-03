/**
 * Tests for FORMAT_CATALOG — completeness, transparency, and browser metadata invariants.
 */
import { describe, it, expect } from 'vitest';
import { FORMAT_CATALOG, BROWSER_SUPPORT } from '../../constants/formatCatalog';
import { OUTPUT_FORMAT } from '../../constants/outputFormat';

describe('FORMAT_CATALOG', () => {
  const expectedFormats: readonly (typeof OUTPUT_FORMAT)[keyof typeof OUTPUT_FORMAT][] = [
    OUTPUT_FORMAT.JPG,
    OUTPUT_FORMAT.PNG,
    OUTPUT_FORMAT.WEBP,
    OUTPUT_FORMAT.AVIF,
  ];

  it('covers all OUTPUT_FORMAT values', () => {
    expectedFormats.forEach((format) => {
      expect(FORMAT_CATALOG).toHaveProperty(format);
    });
  });

  it('JPG has correct transparency and browser support', () => {
    const entry = FORMAT_CATALOG[OUTPUT_FORMAT.JPG];
    expect(entry.supportsTransparency).toBe(false);
    expect(entry.browserSupport).toBe(BROWSER_SUPPORT.WIDE);
    expect(entry.cautions.length).toBeGreaterThan(0);
    expect(entry.cautions[0]).toContain('transparent');
  });

  it('PNG supports transparency and has wide browser support', () => {
    const entry = FORMAT_CATALOG[OUTPUT_FORMAT.PNG];
    expect(entry.supportsTransparency).toBe(true);
    expect(entry.browserSupport).toBe(BROWSER_SUPPORT.WIDE);
    expect(entry.cautions).toHaveLength(0);
  });

  it('WebP supports transparency and has modern browser support', () => {
    const entry = FORMAT_CATALOG[OUTPUT_FORMAT.WEBP];
    expect(entry.supportsTransparency).toBe(true);
    expect(entry.browserSupport).toBe(BROWSER_SUPPORT.MODERN);
    expect(entry.cautions).toHaveLength(0);
  });

  it('AVIF has emerging browser support and non-empty cautions', () => {
    const entry = FORMAT_CATALOG[OUTPUT_FORMAT.AVIF];
    expect(entry.supportsTransparency).toBe(true);
    expect(entry.browserSupport).toBe(BROWSER_SUPPORT.EMERGING);
    expect(entry.cautions.length).toBeGreaterThan(0);
  });

  it('every entry has all required metadata fields', () => {
    const requiredFields = [
      'displayName',
      'description',
      'bestFor',
      'supportsTransparency',
      'browserSupport',
      'cautions',
    ] as const;
    expectedFormats.forEach((format) => {
      const entry = FORMAT_CATALOG[format];
      (requiredFields as readonly string[]).forEach((field) => {
        expect(entry).toHaveProperty(field);
      });
      expect(Array.isArray(entry.cautions)).toBe(true);
    });
  });

  it('displayName is non-empty for all formats', () => {
    expectedFormats.forEach((format) => {
      expect(FORMAT_CATALOG[format].displayName.length).toBeGreaterThan(0);
    });
  });

  it('bestFor is non-empty for all formats', () => {
    expectedFormats.forEach((format) => {
      expect(FORMAT_CATALOG[format].bestFor.length).toBeGreaterThan(0);
    });
  });
});

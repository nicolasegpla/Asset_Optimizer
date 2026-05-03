/**
 * Static catalog of output format metadata for user guidance.
 * Mirrors the constant-driven pattern of PRESET_CATALOG.
 */
import { OUTPUT_FORMAT, type OutputFormat } from './outputFormat';

export const BROWSER_SUPPORT = {
  WIDE: 'wide',
  MODERN: 'modern',
  EMERGING: 'emerging',
} as const;

export type BrowserSupportLevel = (typeof BROWSER_SUPPORT)[keyof typeof BROWSER_SUPPORT];

export interface FormatGuideEntry {
  displayName: string;
  description: string;
  bestFor: string;
  supportsTransparency: boolean;
  browserSupport: BrowserSupportLevel;
  cautions: readonly string[];
}

export const FORMAT_CATALOG: Readonly<Record<OutputFormat, FormatGuideEntry>> = {
  [OUTPUT_FORMAT.JPG]: {
    displayName: 'JPG',
    description: 'Universal web format with excellent compression for photographs.',
    bestFor: 'Photographs, screenshots, and continuous-tone images where file size is critical.',
    supportsTransparency: false,
    browserSupport: BROWSER_SUPPORT.WIDE,
    cautions: ['No alpha channel — transparent areas become solid white.'],
  },
  [OUTPUT_FORMAT.PNG]: {
    displayName: 'PNG',
    description: 'Lossless format that preserves image quality and supports transparency.',
    bestFor: 'Graphics, logos, icons, and any image requiring crisp edges or alpha transparency.',
    supportsTransparency: true,
    browserSupport: BROWSER_SUPPORT.WIDE,
    cautions: [],
  },
  [OUTPUT_FORMAT.WEBP]: {
    displayName: 'WebP',
    description: 'Modern format with superior compression and transparency support.',
    bestFor: 'General-purpose web images where broad compatibility and small file size both matter.',
    supportsTransparency: true,
    browserSupport: BROWSER_SUPPORT.MODERN,
    cautions: [],
  },
  [OUTPUT_FORMAT.AVIF]: {
    displayName: 'AVIF',
    description: 'Next-generation format with the best compression and HDR support.',
    bestFor: 'High-impact visuals where quality and file size are the top priority.',
    supportsTransparency: true,
    browserSupport: BROWSER_SUPPORT.EMERGING,
    cautions: [
      'Encoding is slower, especially for large images.',
      'Browser support is growing but not universal — always verify your audience.',
    ],
  },
} as const;

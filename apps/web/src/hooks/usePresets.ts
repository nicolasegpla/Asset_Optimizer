/**
 * Preset catalog for common optimization use cases.
 * Each preset carries the recommended output configuration for a target surface.
 */
import type { OutputFormat } from '../App';

export const PRESET_IDS = {
  CUSTOM: 'custom',
  ECOMMERCE_PRODUCT: 'ecommerce-product',
  HERO_BANNER: 'hero-banner',
  THUMBNAIL: 'thumbnail',
  OPEN_GRAPH: 'open-graph',
} as const;

export type PresetId = (typeof PRESET_IDS)[keyof typeof PRESET_IDS];

export interface PresetConfig {
  id: PresetId;
  label: string;
  outputFormat: OutputFormat;
  quality: number;
  maxWidth: string;
  maxHeight: string;
}

export const PRESET_CATALOG: readonly PresetConfig[] = [
  {
    id: PRESET_IDS.ECOMMERCE_PRODUCT,
    label: 'E-commerce Product',
    outputFormat: 'webp',
    quality: 80,
    maxWidth: '1200',
    maxHeight: '1200',
  },
  {
    id: PRESET_IDS.HERO_BANNER,
    label: 'Hero / Banner',
    outputFormat: 'webp',
    quality: 85,
    maxWidth: '1920',
    maxHeight: '800',
  },
  {
    id: PRESET_IDS.THUMBNAIL,
    label: 'Thumbnail',
    outputFormat: 'webp',
    quality: 75,
    maxWidth: '300',
    maxHeight: '300',
  },
  {
    id: PRESET_IDS.OPEN_GRAPH,
    label: 'Open Graph',
    outputFormat: 'jpg',
    quality: 85,
    maxWidth: '1200',
    maxHeight: '630',
  },
] as const;

export type { OutputFormat };

export interface PresetApplyResult {
  outputFormat: OutputFormat;
  quality: number;
  maxWidth: string;
  maxHeight: string;
}

/**
 * Apply a preset by ID, returning its configuration.
 * Returns null if the preset ID is not found.
 */
export function applyPreset(presetId: PresetId): PresetApplyResult | null {
  if (presetId === PRESET_IDS.CUSTOM) {
    return null;
  }
  const preset = PRESET_CATALOG.find((p) => p.id === presetId);
  if (!preset) return null;
  return {
    outputFormat: preset.outputFormat,
    quality: preset.quality,
    maxWidth: preset.maxWidth,
    maxHeight: preset.maxHeight,
  };
}

/**
 * Check whether current field values match a known preset exactly.
 * Returns the matched preset ID or CUSTOM if no match.
 */
export function matchPresetOrCustom(
  outputFormat: OutputFormat,
  quality: number,
  maxWidth: string,
  maxHeight: string,
): PresetId {
  const matched = PRESET_CATALOG.find(
    (p) =>
      p.outputFormat === outputFormat &&
      p.quality === quality &&
      p.maxWidth === maxWidth &&
      p.maxHeight === maxHeight,
  );
  return matched ? matched.id : PRESET_IDS.CUSTOM;
}
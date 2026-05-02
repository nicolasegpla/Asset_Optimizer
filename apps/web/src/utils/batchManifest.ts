/**
 * Parse and validate manifest.json from a batch ZIP Blob.
 * Returns null if manifest is missing or corrupt (caller falls back to header-only).
 */
export interface BatchManifestFile {
  source: string;
  output: string;
  originalBytes: number;
  optimizedBytes: number;
  compressionRatio: number;
  originalFormat: string;
  outputFormat: string;
  originalDimensions: { width: number; height: number };
  outputDimensions: { width: number; height: number };
}

export interface BatchManifestError {
  source: string;
  code: string;
  message: string;
}

export interface BatchManifestSummary {
  totalFiles: number;
  processedFiles: number;
  failedFiles: number;
  totalOriginalBytes: number;
  totalOptimizedBytes: number;
}

export interface BatchManifest {
  files: BatchManifestFile[];
  errors: BatchManifestError[];
  summary: BatchManifestSummary;
}

export interface ParsedManifest {
  manifest: BatchManifest;
  zipBlob: Blob;
}

import { loadJsZip } from './loadJsZip';

async function _loadJSZip(): Promise<typeof import('jszip')> {
  const JSZip = await loadJsZip();
  return JSZip;
}

/**
 * Lazily load JSZip, parse manifest.json from a ZIP Blob.
 * Returns null on any failure (missing file, corrupt JSON, schema mismatch).
 */
export async function parseManifestFromZip(zipBlob: Blob): Promise<BatchManifest | null> {
  try {
    const JSZip = await _loadJSZip();
    const zip = await JSZip.loadAsync(zipBlob);
    const manifestFile = zip.file("manifest.json");
    if (!manifestFile) {
      return null;
    }
    const manifestText = await manifestFile.async("string");
    const parsed = JSON.parse(manifestText) as unknown;

    // Runtime schema validation — ensure required top-level keys exist
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("files" in parsed) ||
      !("errors" in parsed) ||
      !("summary" in parsed)
    ) {
      return null;
    }

    return parsed as BatchManifest;
  } catch {
    // Corrupt ZIP, missing manifest.json, or invalid JSON — fall back gracefully
    return null;
  }
}

/**
 * Compute total savings percentage from byte totals.
 */
export function computeSavingsPercent(originalBytes: number, optimizedBytes: number): number {
  if (originalBytes === 0 || optimizedBytes >= originalBytes) return 0;
  return Math.round(((originalBytes - optimizedBytes) / originalBytes) * 100);
}

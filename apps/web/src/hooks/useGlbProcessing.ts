/**
 * GLB processing: builds FormData, calls /api/v1/optimize-glb, maps result.
 *
 * Encapsulates the GLB optimize request lifecycle:
 * - constructing FormData with files + naming options
 * - handling single-file vs ZIP download flows
 * - result state management (success/error)
 * - batch manifest extraction via lazy-loaded JSZip
 *
 * Mirrors useImageProcessing patterns but without image-specific features
 * (no quality, dimensions, output format, or image preview).
 */
import { useState } from 'react';
import { buildPathsPayload } from '../upload-paths';
import type { ProcessingState } from '../App';
import { extractApiError } from '../utils/apiErrors';
import { parseManifestFromZip } from '../utils/batchManifest';
import { loadJsZip } from '../utils/loadJsZip';

export interface GlbProcessingState {
  isProcessing: boolean;
  result: ProcessingState;
}

export interface UseGlbProcessingReturn extends GlbProcessingState {
  handleOptimize: (options: GlbOptimizeOptions) => Promise<boolean>;
  clearResult: () => void;
}

export interface GlbOptimizeOptions {
  files: File[];
  zipName?: string;
  outputPrefix?: string;
  outputSuffix?: string;
  outputStem?: string;
  selectionSummary?: {
    invalidFileNames: string[];
    skippedCount: number;
    validCount: number;
  };
}

function parseNumericHeader(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function useGlbProcessing(): UseGlbProcessingReturn {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ProcessingState>(null);

  const clearResult = () => {
    setResult(null);
  };

  const handleOptimize = async ({
    files,
    zipName,
    outputPrefix,
    outputSuffix,
    outputStem,
    selectionSummary,
  }: GlbOptimizeOptions) => {
    if (!files.length) return false;

    setIsProcessing(true);
    setResult(null);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append('files', file);
      }

      const pathsPayload = buildPathsPayload(files);
      if (pathsPayload !== null) {
        formData.append('paths', pathsPayload);
      }
      if (zipName) formData.append('zip_name', zipName);
      // Prefix/suffix only for single-file downloads
      if (outputPrefix && files.length === 1) formData.append('output_prefix', outputPrefix);
      if (outputSuffix && files.length === 1) formData.append('output_suffix', outputSuffix);
      // output_stem only for batch/folder downloads
      if (outputStem && files.length > 1) formData.append('output_stem', outputStem);

      const response = await fetch(`${API_BASE_URL}/api/v1/optimize-glb`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorPayload = await response.json();
        setResult(extractApiError(errorPayload));
        setIsProcessing(false);
        return false;
      }

      const contentType = response.headers.get('Content-Type') ?? '';
      const isZip = contentType.includes('zip');

      const originalBytes = response.headers.get('X-Asset-Original-Bytes');
      const optimizedBytes = response.headers.get('X-Asset-Optimized-Bytes');
      const compressionRatio = response.headers.get('X-Asset-Compression-Ratio');
      const processedCount = response.headers.get('X-Asset-Processed-Count');

      if (isZip) {
        const blob = await response.blob();
        const errorCountHeader = response.headers.get('X-Asset-Error-Count');
        const errorCount = errorCountHeader ? Number(errorCountHeader) : null;

        // Extract manifest lazily via JSZip
        const manifest = await parseManifestFromZip(blob);

        const disposition = response.headers.get('Content-Disposition') ?? '';
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
        const zipFileName = filenameMatch ? filenameMatch[1] : 'optimized-assets.zip';

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = zipFileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        setResult({
          type: 'success',
          compressionRatio: null,
          originalBytes: originalBytes ? Number(originalBytes) : null,
          originalFormat: null,
          originalHeight: null,
          originalWidth: null,
          optimizedBytes: optimizedBytes ? Number(optimizedBytes) : null,
          outputFormat: null,
          outputHeight: null,
          outputWidth: null,
          processedCount: processedCount ? Number(processedCount) : null,
          downloadedFileName: zipFileName,
          manifest,
          errorCount,
          batchSelectionSummary: selectionSummary ?? null,
        });
        return true;
      } else {
        const disposition = response.headers.get('Content-Disposition') ?? '';
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
        const downloadedFileName = filenameMatch ? filenameMatch[1] : 'asset.glb';

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadedFileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        setResult({
          type: 'success',
          compressionRatio: compressionRatio ? parseFloat(compressionRatio) : null,
          originalBytes: originalBytes ? Number(originalBytes) : null,
          originalFormat: 'glb',
          originalHeight: null,
          originalWidth: null,
          optimizedBytes: optimizedBytes ? Number(optimizedBytes) : null,
          outputFormat: 'glb',
          outputHeight: null,
          outputWidth: null,
          processedCount: 1,
          downloadedFileName,
          manifest: null,
          errorCount: null,
          batchSelectionSummary: null,
        });
        return true;
      }
    } catch (err) {
      setResult({
        type: 'error',
        code: 'NETWORK_ERROR',
        hint: 'Check that the API is running and try again.',
        message: err instanceof Error ? err.message : 'Network error occurred.',
        title: 'We could not reach the server',
      });
      return false;
    } finally {
      setIsProcessing(false);
    }
  };

  return {
    isProcessing,
    result,
    handleOptimize,
    clearResult,
  };
}

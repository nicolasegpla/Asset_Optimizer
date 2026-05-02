/**
 * Image processing: builds FormData, calls /api/v1/transform, maps result.
 *
 * Encapsulates the optimize request lifecycle:
 * - constructing FormData with files + settings
 * - handling single-file vs ZIP download flows
 * - result state management (success/error)
 * - preview URL lifecycle for single-file comparison view
 * - batch manifest extraction via lazy-loaded JSZip
 */
import { useState } from 'react';
import type { OutputFormat } from '../App';
import { buildPathsPayload } from '../upload-paths';
import type { ImageComparisonPreview, ProcessingState } from '../App';
import { extractApiError } from '../App';
import { parseManifestFromZip } from '../utils/batchManifest';

export interface ImageProcessingState {
  isProcessing: boolean;
  result: ProcessingState;
  imageComparisonPreview: ImageComparisonPreview | null;
  comparisonPosition: number;
}

export interface UseImageProcessingReturn extends ImageProcessingState {
  setComparisonPosition: (position: number) => void;
  handleOptimize: (options: OptimizeOptions) => Promise<boolean>;
  replaceImageComparisonPreview: (next: ImageComparisonPreview | null) => void;
  clearResult: () => void;
}

export interface OptimizeOptions {
  files: File[];
  outputFormat: OutputFormat;
  quality: number;
  maxWidth: string;
  maxHeight: string;
}

function parseNumericHeader(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function useImageProcessing(): UseImageProcessingReturn {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ProcessingState>(null);
  const [imageComparisonPreview, setImageComparisonPreview] = useState<ImageComparisonPreview | null>(null);
  const [comparisonPosition, setComparisonPosition] = useState(50);

  const replaceImageComparisonPreview = (next: ImageComparisonPreview | null) => {
    setImageComparisonPreview((current) => {
      if (current) {
        URL.revokeObjectURL(current.originalUrl);
        URL.revokeObjectURL(current.optimizedUrl);
      }
      return next;
    });
  };

  const clearResult = () => {
    setResult(null);
    replaceImageComparisonPreview(null);
  };

  const handleOptimize = async ({
    files,
    outputFormat,
    quality,
    maxWidth,
    maxHeight,
  }: OptimizeOptions) => {
    if (!files.length) return false;

    setIsProcessing(true);
    setResult(null);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append('files', file);
      }
      formData.append('output_format', outputFormat);
      formData.append('quality', String(quality));
      if (maxWidth) formData.append('max_width', maxWidth);
      if (maxHeight) formData.append('max_height', maxHeight);

      const pathsPayload = buildPathsPayload(files);
      if (pathsPayload !== null) {
        formData.append('paths', pathsPayload);
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/transform`, {
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
      const originalFormat = response.headers.get('X-Asset-Original-Format');
      const outputFormatHeader = response.headers.get('X-Asset-Output-Format');
      const originalWidth = parseNumericHeader(response.headers.get('X-Asset-Original-Width'));
      const originalHeight = parseNumericHeader(response.headers.get('X-Asset-Original-Height'));
      const outputWidth = parseNumericHeader(response.headers.get('X-Asset-Output-Width'));
      const outputHeight = parseNumericHeader(response.headers.get('X-Asset-Output-Height'));

      if (isZip) {
        const blob = await response.blob();
        const errorCountHeader = response.headers.get('X-Asset-Error-Count');
        const errorCount = errorCountHeader ? Number(errorCountHeader) : null;

        // Extract manifest lazily via JSZip
        const manifest = await parseManifestFromZip(blob);

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'optimized-assets.zip';
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
          downloadedFileName: 'optimized-assets.zip',
          manifest,
          errorCount,
        });
        return true;
      } else {
        const disposition = response.headers.get('Content-Disposition') ?? '';
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
        const downloadedFileName = filenameMatch ? filenameMatch[1] : 'asset';
        const originalFile = files[0];

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const originalUrl = URL.createObjectURL(originalFile);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadedFileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        setResult({
          type: 'success',
          compressionRatio: compressionRatio ? parseFloat(compressionRatio) : null,
          originalBytes: originalBytes ? Number(originalBytes) : null,
          originalFormat,
          originalHeight,
          originalWidth,
          optimizedBytes: optimizedBytes ? Number(optimizedBytes) : null,
          outputFormat: outputFormatHeader,
          outputHeight,
          outputWidth,
          processedCount: 1,
          downloadedFileName,
          manifest: null,
          errorCount: null,
        });
        replaceImageComparisonPreview({
          optimizedUrl: url,
          originalName: originalFile.name,
          originalUrl,
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
    imageComparisonPreview,
    comparisonPosition,
    setComparisonPosition,
    handleOptimize,
    replaceImageComparisonPreview,
    clearResult,
  };
}

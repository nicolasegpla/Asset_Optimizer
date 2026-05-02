import { useEffect, useRef, useState } from 'react';

const OUTPUT_FORMAT = {
    JPG: 'jpg',
    PNG: 'png',
    WEBP: 'webp',
    AVIF: 'avif',
} as const;

const SUPPORTED_INPUT_FORMAT = {
    JPG: 'jpg',
    JPEG: 'jpeg',
    PNG: 'png',
    WEBP: 'webp',
} as const;

type OutputFormat = (typeof OUTPUT_FORMAT)[keyof typeof OUTPUT_FORMAT];
type SupportedInputFormat = (typeof SUPPORTED_INPUT_FORMAT)[keyof typeof SUPPORTED_INPUT_FORMAT];

interface BackendStatus {
    message: string;
    service: string;
    status: string;
}

interface SelectedFile {
    name: string;
    relativePath: string;
    sizeInBytes: number;
}

interface SelectionSummary {
    invalidFileNames: string[];
    skippedCount: number;
    validCount: number;
}

interface ImageComparisonPreview {
    optimizedUrl: string;
    originalName: string;
    originalUrl: string;
}

interface ProcessingResult {
    type: 'success';
    compressionRatio: number | null;
    originalBytes: number | null;
    originalFormat: string | null;
    originalHeight: number | null;
    originalWidth: number | null;
    optimizedBytes: number | null;
    outputFormat: string | null;
    outputHeight: number | null;
    outputWidth: number | null;
    processedCount: number | null;
    downloadedFileName: string | null;
}

interface ProcessingError {
    type: 'error';
    code: string;
    message: string;
}

interface ApiErrorDetail {
    code?: string;
    message?: string;
}

interface ApiErrorShape {
    error?: ApiErrorDetail;
}

interface ApiErrorResponse {
    detail?: ApiErrorShape | ApiErrorShape[] | string;
    error?: ApiErrorDetail;
}

type ProcessingState = ProcessingResult | ProcessingError | null;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const SUPPORTED_INPUT_FORMAT_VALUES = Object.values(SUPPORTED_INPUT_FORMAT) as SupportedInputFormat[];
const INPUT_ACCEPT = '.jpg,.jpeg,.png,.webp';

function extractApiError(payload: ApiErrorResponse): ProcessingError {
    const nestedError =
        typeof payload.detail === 'object' && payload.detail !== null && !Array.isArray(payload.detail)
            ? payload.detail.error
            : undefined;

    const directError = payload.error;
    const resolvedError = nestedError ?? directError;

    return {
        type: 'error',
        code: resolvedError?.code ?? 'UNKNOWN_ERROR',
        message:
            resolvedError?.message ??
            (typeof payload.detail === 'string' ? payload.detail : 'An unknown error occurred.'),
    };
}

function getFileExtension(fileName: string): string {
    const parts = fileName.toLowerCase().split('.');
    return parts.length > 1 ? parts[parts.length - 1] : '';
}

function isSupportedInputFile(file: File): boolean {
    return SUPPORTED_INPUT_FORMAT_VALUES.includes(getFileExtension(file.name) as SupportedInputFormat);
}

function parseNumericHeader(value: string | null): number | null {
    if (!value) {
        return null;
    }

    const parsedValue = Number(value);
    return Number.isFinite(parsedValue) ? parsedValue : null;
}

export function App() {
    const filesInputRef = useRef<HTMLInputElement | null>(null);
    const folderInputRef = useRef<HTMLInputElement | null>(null);

    const [backendStatus, setBackendStatus] = useState('checking');
    const [outputFormat, setOutputFormat] = useState<OutputFormat>(OUTPUT_FORMAT.WEBP);
    const [quality, setQuality] = useState(80);
    const [maxWidth, setMaxWidth] = useState('');
    const [maxHeight, setMaxHeight] = useState('');
    const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
    const [selectedUploadFiles, setSelectedUploadFiles] = useState<File[]>([]);
    const [selectionSummary, setSelectionSummary] = useState<SelectionSummary | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [imageComparisonPreview, setImageComparisonPreview] = useState<ImageComparisonPreview | null>(null);
    const [comparisonPosition, setComparisonPosition] = useState(50);
    const [result, setResult] = useState<ProcessingState>(null);

    useEffect(() => {
        const checkApi = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/health`);

                if (!response.ok) {
                    throw new Error('API healthcheck failed');
                }

                const data = (await response.json()) as BackendStatus;
                setBackendStatus(data.status);
            } catch {
                setBackendStatus('offline');
            }
        };

        void checkApi();
    }, []);

    useEffect(() => {
        return () => {
            if (imageComparisonPreview) {
                URL.revokeObjectURL(imageComparisonPreview.originalUrl);
                URL.revokeObjectURL(imageComparisonPreview.optimizedUrl);
            }
        };
    }, [imageComparisonPreview]);

    const totalSizeLabel = (() => {
        const totalSize = selectedFiles.reduce((acc, file) => acc + file.sizeInBytes, 0);
        return new Intl.NumberFormat('en-US', {
            maximumFractionDigits: 2,
            style: 'unit',
            unit: 'megabyte',
        }).format(totalSize / 1024 / 1024);
    })();

    const resetFileInputs = () => {
        if (filesInputRef.current) {
            filesInputRef.current.value = '';
        }

        if (folderInputRef.current) {
            folderInputRef.current.value = '';
        }
    };

    const clearSelection = () => {
        setSelectedFiles([]);
        setSelectedUploadFiles([]);
        setSelectionSummary(null);
        setComparisonPosition(50);
        resetFileInputs();
    };

    const replaceImageComparisonPreview = (nextPreview: ImageComparisonPreview | null) => {
        setImageComparisonPreview((currentPreview) => {
            if (currentPreview) {
                URL.revokeObjectURL(currentPreview.originalUrl);
                URL.revokeObjectURL(currentPreview.optimizedUrl);
            }

            return nextPreview;
        });
    };

    const handleSelection = (files: FileList | null) => {
        if (!files) {
            clearSelection();
            setResult(null);
            return;
        }

        const uploadFiles = Array.from(files);
        replaceImageComparisonPreview(null);
        const validFiles = uploadFiles.filter(isSupportedInputFile);
        const invalidFiles = uploadFiles.filter((file) => !isSupportedInputFile(file));

        if (!validFiles.length) {
            clearSelection();
            setResult({
                type: 'error',
                code: 'UNSUPPORTED_INPUT_SELECTION',
                message: 'Only JPG, JPEG, PNG, and WEBP files are allowed.',
            });
            return;
        }

        setSelectionSummary({
            invalidFileNames: invalidFiles.slice(0, 3).map((file) => file.name),
            skippedCount: invalidFiles.length,
            validCount: validFiles.length,
        });

        if (invalidFiles.length) {
            setResult({
                type: 'error',
                code: 'UNSUPPORTED_INPUT_SELECTION',
                message: `${invalidFiles.length} unsupported file(s) were skipped. Only JPG, JPEG, PNG, and WEBP are allowed.`,
            });
        } else {
            setResult(null);
        }

        const normalizedFiles = validFiles.map((file) => ({
            name: file.name,
            relativePath: file.webkitRelativePath || file.name,
            sizeInBytes: file.size,
        }));

        setSelectedFiles(normalizedFiles);
        setSelectedUploadFiles(validFiles);
    };

    const handleOptimize = async () => {
        if (!selectedUploadFiles.length) return;

        setIsProcessing(true);
        setResult(null);

        try {
            const formData = new FormData();

            for (const file of selectedUploadFiles) {
                formData.append('files', file);
            }
            formData.append('output_format', outputFormat);
            formData.append('quality', String(quality));
            if (maxWidth) formData.append('max_width', maxWidth);
            if (maxHeight) formData.append('max_height', maxHeight);

            const response = await fetch(`${API_BASE_URL}/api/v1/transform`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorPayload = (await response.json()) as ApiErrorResponse;
                setResult(extractApiError(errorPayload));
                setIsProcessing(false);
                return;
            }

            // Determine if ZIP or single file from Content-Type
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
                });
                clearSelection();
            } else {
                // Single file — extract filename from Content-Disposition
                const disposition = response.headers.get('Content-Disposition') ?? '';
                const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
                const downloadedFileName = filenameMatch ? filenameMatch[1] : 'asset';
                const originalFile = selectedUploadFiles[0];

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
                });
                replaceImageComparisonPreview({
                    optimizedUrl: url,
                    originalName: originalFile.name,
                    originalUrl,
                });
                clearSelection();
            }
        } catch (err) {
            setResult({
                type: 'error',
                code: 'NETWORK_ERROR',
                message: err instanceof Error ? err.message : 'Network error occurred.',
            });
        } finally {
            setIsProcessing(false);
        }
    };

    const formatBytes = (bytes: number | null): string => {
        if (bytes === null) return '—';
        return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(bytes / 1024) + ' KB';
    };

    const formatDimensions = (width: number | null, height: number | null): string => {
        if (width === null || height === null) {
            return '—';
        }

        return `${width}×${height}`;
    };

    return (
        <main className="page">
            <section className="hero">
                <p className="eyebrow">Asset Optimizer</p>
                <h1>Prepare web-ready images without friction.</h1>
                <p className="description">
                    Convert, compress, resize, and package image assets for websites, e-commerce,
                    and digital products.
                </p>

                <div className="status-row">
                    <span className={`badge badge-${backendStatus}`}>API: {backendStatus}</span>
                    <span className="badge badge-neutral">Docker-ready monorepo</span>
                </div>
            </section>

            <section className="card grid">
                <div className="column">
                    <h2>Source assets</h2>

                    <label className="picker">
                        <span>Select files</span>
                        <input
                            ref={filesInputRef}
                            accept={INPUT_ACCEPT}
                            multiple
                            type="file"
                            onChange={(event) => handleSelection(event.target.files)}
                        />
                        <small className="format-hint">Supported input formats: JPG, JPEG, PNG, WEBP.</small>
                    </label>

                    <label className="picker">
                        <span>Select folder</span>
                        <input
                            ref={folderInputRef}
                            accept={INPUT_ACCEPT}
                            multiple
                            type="file"
                            webkitdirectory=""
                            directory=""
                            onChange={(event) => handleSelection(event.target.files)}
                        />
                        <small className="format-hint">
                            Folder uploads can include only JPG, JPEG, PNG, and WEBP files.
                        </small>
                    </label>

                    <div className="summary-box">
                        <strong>{selectedFiles.length}</strong>
                        <span>files selected</span>
                        <span>{totalSizeLabel} total</span>
                        {selectionSummary && (
                            <>
                                <span>{selectionSummary.validCount} valid file(s) ready</span>
                                {selectionSummary.skippedCount > 0 && (
                                    <div className="selection-warning">
                                        <span>{selectionSummary.skippedCount} unsupported file(s) skipped</span>
                                        <span>
                                            Skipped: {selectionSummary.invalidFileNames.join(', ')}
                                            {selectionSummary.skippedCount > selectionSummary.invalidFileNames.length
                                                ? ', ...'
                                                : ''}
                                        </span>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>

                <div className="column">
                    <h2>Transformation settings</h2>

                    <label>
                        <span>Output format</span>
                        <select
                            value={outputFormat}
                            onChange={(event) => setOutputFormat(event.target.value as OutputFormat)}
                        >
                            {Object.values(OUTPUT_FORMAT).map((format) => (
                                <option key={format} value={format}>
                                    {format.toUpperCase()}
                                </option>
                            ))}
                        </select>
                        {outputFormat === 'avif' && (
                            <small className="format-hint">AVIF encoding takes longer for large images.</small>
                        )}
                    </label>

                    <label>
                        <span>Quality</span>
                        <input
                            max={100}
                            min={1}
                            type="range"
                            value={quality}
                            onChange={(event) => setQuality(Number(event.target.value))}
                        />
                        <small>{quality}%</small>
                    </label>

                    <div className="dimension-grid">
                        <label>
                            <span>Max width</span>
                            <input
                                placeholder="1200"
                                type="number"
                                value={maxWidth}
                                onChange={(event) => setMaxWidth(event.target.value)}
                            />
                        </label>

                        <label>
                            <span>Max height</span>
                            <input
                                placeholder="1200"
                                type="number"
                                value={maxHeight}
                                onChange={(event) => setMaxHeight(event.target.value)}
                            />
                        </label>
                    </div>

                    <button
                        className="primary-button"
                        type="button"
                        disabled={!selectedUploadFiles.length || isProcessing}
                        onClick={handleOptimize}
                    >
                        {isProcessing ? 'Processing…' : 'Optimize & Download'}
                    </button>
                </div>
            </section>

            {result && result.type === 'error' && (
                <section className="card error-card">
                    <h2>Error</h2>
                    <p className="error-message">
                        <strong>[{result.code}]</strong> {result.message}
                    </p>
                </section>
            )}

            {result && result.type === 'success' && (
                <section className="card result-card">
                    <h2>Result</h2>
                    {result.processedCount === 1 ? (
                        <div className="result-summary">
                            <p>
                                <strong>{result.downloadedFileName}</strong> downloaded successfully.
                            </p>
                            <div className="size-comparison">
                                <span>Original: {formatBytes(result.originalBytes)}</span>
                                <span>→</span>
                                <span>Optimized: {formatBytes(result.optimizedBytes)}</span>
                                <span className="ratio-badge">
                                    {result.compressionRatio !== null ? `-${result.compressionRatio.toFixed(1)}%` : '—'}
                                </span>
                            </div>
                            {imageComparisonPreview && (
                                <div className="comparison-panel">
                                    <div className="comparison-labels">
                                        <span>Before</span>
                                        <span>After</span>
                                    </div>

                                    <div className="comparison-stage">
                                        <img
                                            className="comparison-image"
                                            src={imageComparisonPreview.originalUrl}
                                            alt={`Original ${imageComparisonPreview.originalName}`}
                                        />
                                        <div
                                            className="comparison-overlay"
                                            style={{ clipPath: `inset(0 0 0 ${comparisonPosition}%)` }}
                                        >
                                            <img
                                                className="comparison-image comparison-image-overlay"
                                                src={imageComparisonPreview.optimizedUrl}
                                                alt={`Optimized ${result.downloadedFileName ?? 'image'}`}
                                            />
                                        </div>
                                        <div
                                            className="comparison-divider"
                                            style={{ left: `${comparisonPosition}%` }}
                                        />
                                    </div>

                                    <label className="comparison-slider">
                                        <span>Comparison slider: {comparisonPosition}%</span>
                                        <input
                                            min={0}
                                            max={100}
                                            step={1}
                                            type="range"
                                            value={comparisonPosition}
                                            onChange={(event) =>
                                                setComparisonPosition(Number(event.target.value))
                                            }
                                        />
                                    </label>

                                    <div className="comparison-caption">
                                        <span>
                                            {imageComparisonPreview.originalName} ·{' '}
                                            {(result.originalFormat ?? 'unknown').toUpperCase()} ·{' '}
                                            {formatDimensions(result.originalWidth, result.originalHeight)}
                                        </span>
                                        <span>
                                            {(result.downloadedFileName ?? 'optimized image')} ·{' '}
                                            {(result.outputFormat ?? outputFormat).toUpperCase()} ·{' '}
                                            {formatDimensions(result.outputWidth, result.outputHeight)}
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="result-summary">
                            <p>
                                <strong>{result.processedCount} files</strong> packaged into{' '}
                                <strong>{result.downloadedFileName}</strong>.
                            </p>
                            <div className="size-comparison">
                                <span>Original: {formatBytes(result.originalBytes)}</span>
                                <span>→</span>
                                <span>Optimized: {formatBytes(result.optimizedBytes)}</span>
                            </div>
                        </div>
                    )}
                </section>
            )}

            <section className="card">
                <h2>Current batch preview</h2>
                {selectedFiles.length === 0 ? (
                    <p className="empty-state">No files selected yet.</p>
                ) : (
                    <ul className="file-list">
                        {selectedFiles.slice(0, 8).map((file) => (
                            <li key={file.relativePath}>
                                <span>{file.relativePath}</span>
                                <strong>{Math.round(file.sizeInBytes / 1024)} KB</strong>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </main>
    );
}

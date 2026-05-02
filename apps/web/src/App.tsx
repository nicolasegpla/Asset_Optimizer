import { useEffect, useRef, useState } from 'react';

import packageInfo from '../package.json';
import { HeroSection } from './components/HeroSection';
import { SourcePanel } from './components/SourcePanel';
import { SettingsPanel } from './components/SettingsPanel';
import { ResultPanel } from './components/ResultPanel';
import { FileList } from './components/FileList';
import { useBackendStatus, DEFAULT_LIMITS } from './hooks/useBackendStatus';
import { useImageProcessing } from './hooks/useImageProcessing';
import { filterSystemFiles } from './utils/fileFilters';

// ─── Constants ───────────────────────────────────────────────────────────────────

export const OUTPUT_FORMAT = {
    JPG: 'jpg',
    PNG: 'png',
    WEBP: 'webp',
    AVIF: 'avif',
} as const;

export type OutputFormat = (typeof OUTPUT_FORMAT)[keyof typeof OUTPUT_FORMAT];

const SUPPORTED_INPUT_FORMAT = {
    JPG: 'jpg',
    JPEG: 'jpeg',
    PNG: 'png',
    WEBP: 'webp',
} as const;

type SupportedInputFormat = (typeof SUPPORTED_INPUT_FORMAT)[keyof typeof SUPPORTED_INPUT_FORMAT];

export const SUPPORTED_INPUT_FORMAT_VALUES = Object.values(SUPPORTED_INPUT_FORMAT) as SupportedInputFormat[];

// ─── Shared types ─────────────────────────────────────────────────────────────────

export interface BackendStatus {
    message: string;
    service: string;
    status: string;
}

export interface SelectedFile {
    name: string;
    relativePath: string;
    sizeInBytes: number;
}

export interface SelectionSummary {
    invalidFileNames: string[];
    skippedCount: number;
    validCount: number;
}

export interface ImageComparisonPreview {
    optimizedUrl: string;
    originalName: string;
    originalUrl: string;
}

export interface ProcessingResult {
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
    // Batch-specific fields (populated for ZIP responses via JSZip manifest extraction)
    manifest: import('./utils/batchManifest').BatchManifest | null;
    errorCount: number | null;
}

export interface ProcessingError {
    type: 'error';
    code: string;
    hint: string | null;
    message: string;
    title: string;
}

export type ProcessingState = ProcessingResult | ProcessingError | null;

// ─── Error resolution ───────────────────────────────────────────────────────────

const ERROR_COPY = {
    FILE_COUNT_LIMIT: {
        hint: 'Try a smaller batch with fewer than 100 files.',
        title: 'Too many files selected',
    },
    INVALID_DIMENSIONS: {
        hint: 'Use width and height values between 1 and 10000 pixels.',
        title: 'The resize dimensions are invalid',
    },
    INVALID_IMAGE: {
        hint: 'Make sure the selected files are real, supported images and not corrupted system files.',
        title: 'We could not process one or more images',
    },
    INVALID_PATHS_FORMAT: {
        hint: 'Try selecting the folder again so we can rebuild its internal structure correctly.',
        title: 'We could not read the folder structure',
    },
    INVALID_QUALITY: {
        hint: 'Choose a quality value between 1 and 100.',
        title: 'The quality value is not valid',
    },
    NETWORK_ERROR: {
        hint: 'Check that the API is running and try again.',
        title: 'We could not reach the server',
    },
    PROCESSING_TIMEOUT: {
        hint: 'Try fewer files, smaller images, or a faster output format.',
        title: 'The transformation took too long',
    },
    TOTAL_SIZE_LIMIT: {
        hint: 'Reduce the number of files or use smaller images before uploading.',
        title: 'The upload is too large',
    },
    UNSUPPORTED_INPUT_FORMAT: {
        hint: 'Use JPG, JPEG, PNG, or WEBP files only.',
        title: 'Some selected files are not supported',
    },
    UNSUPPORTED_INPUT_SELECTION: {
        hint: 'Remove unsupported files and keep only JPG, JPEG, PNG, or WEBP images.',
        title: 'Your selection contains unsupported files',
    },
    UNSUPPORTED_OUTPUT_FORMAT: {
        hint: 'Pick one of the formats available in the output selector.',
        title: 'The output format is not available',
    },
    UNKNOWN_ERROR: {
        hint: 'Please try again. If it keeps happening, review the selected files and settings.',
        title: 'Something went wrong',
    },
} as const;

type ErrorCodeKey = keyof typeof ERROR_COPY;

function resolveFriendlyErrorCopy(code: string) {
    return ERROR_COPY[(code in ERROR_COPY ? code : 'UNKNOWN_ERROR') as ErrorCodeKey];
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

export function extractApiError(payload: ApiErrorResponse): ProcessingError {
    const nestedError =
        typeof payload.detail === 'object' && payload.detail !== null && !Array.isArray(payload.detail)
            ? payload.detail.error
            : undefined;

    const directError = payload.error;
    const resolvedError = nestedError ?? directError;
    const code = resolvedError?.code ?? 'UNKNOWN_ERROR';
    const friendlyCopy = resolveFriendlyErrorCopy(code);

    return {
        type: 'error',
        code,
        hint: friendlyCopy.hint,
        message:
            resolvedError?.message ??
            (typeof payload.detail === 'string' ? payload.detail : 'An unknown error occurred.'),
        title: friendlyCopy.title,
    };
}

// ─── App ─────────────────────────────────────────────────────────────────────────

function getFileExtension(fileName: string): string {
    const parts = fileName.toLowerCase().split('.');
    return parts.length > 1 ? parts[parts.length - 1] : '';
}

function isSupportedInputFile(file: File): boolean {
    return SUPPORTED_INPUT_FORMAT_VALUES.includes(getFileExtension(file.name) as SupportedInputFormat);
}

export function App() {
    const filesInputRef = useRef<HTMLInputElement | null>(null);
    const folderInputRef = useRef<HTMLInputElement | null>(null);

    const { apiStatus, limits } = useBackendStatus();
    const {
        isProcessing,
        result,
        imageComparisonPreview,
        comparisonPosition,
        setComparisonPosition,
        handleOptimize,
        clearResult,
    } = useImageProcessing();

    const [outputFormat, setOutputFormat] = useState<OutputFormat>(OUTPUT_FORMAT.WEBP);
    const [quality, setQuality] = useState(80);
    const [maxWidth, setMaxWidth] = useState('');
    const [maxHeight, setMaxHeight] = useState('');
    const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
    const [selectedUploadFiles, setSelectedUploadFiles] = useState<File[]>([]);
    const [selectionSummary, setSelectionSummary] = useState<SelectionSummary | null>(null);

    useEffect(() => {
        return () => {
            if (imageComparisonPreview) {
                URL.revokeObjectURL(imageComparisonPreview.originalUrl);
                URL.revokeObjectURL(imageComparisonPreview.optimizedUrl);
            }
        };
    }, [imageComparisonPreview]);

    const currentTotalBytes = selectedFiles.reduce((acc, file) => acc + file.sizeInBytes, 0);

    const resetFileInputs = () => {
        if (filesInputRef.current) {
            filesInputRef.current.value = '';
        }
        if (folderInputRef.current) {
            folderInputRef.current.value = '';
        }
    };

    const resetSelectionState = () => {
        setSelectedFiles([]);
        setSelectedUploadFiles([]);
        setSelectionSummary(null);
    };

    const clearSelection = () => {
        resetSelectionState();
        clearResult();
        resetFileInputs();
    };

    const handleSelection = (files: FileList | null) => {
        if (!files) {
            clearSelection();
            return;
        }

        // 1. Filter junk/system files FIRST (before format validation)
        const filterResult = filterSystemFiles(files);
        const junkCount = filterResult.filteredCount;

        // 2. Filter to supported input formats from the accepted files
        const uploadFiles = Array.from(filterResult.accepted);
        const validFiles = uploadFiles.filter(isSupportedInputFile);
        const invalidFiles = uploadFiles.filter((file) => !isSupportedInputFile(file));

        // Build list of all rejected files for user feedback
        const allRejectedNames = [
            ...filterResult.filteredNames,
            ...invalidFiles.slice(0, 3).map((f) => f.name),
        ];

        if (!validFiles.length) {
            clearSelection();
            setSelectionSummary({
                invalidFileNames: allRejectedNames,
                skippedCount: junkCount + invalidFiles.length,
                validCount: 0,
            });
            clearResult();
            return;
        }

        // Show skipped file info (system/junk + unsupported)
        const totalSkipped = junkCount + invalidFiles.length;
        if (totalSkipped > 0) {
            setSelectionSummary({
                invalidFileNames: allRejectedNames,
                skippedCount: totalSkipped,
                validCount: validFiles.length,
            });
        } else {
            setSelectionSummary(null);
        }

        const normalizedFiles = validFiles.map((file) => ({
            name: file.name,
            relativePath: (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name,
            sizeInBytes: file.size,
        }));

        setSelectedFiles(normalizedFiles);
        setSelectedUploadFiles(validFiles);
    };

    return (
        <main className="page">
            <HeroSection backendStatus={apiStatus} />

            <section className="card grid">
                <SourcePanel
                    filesInputRef={filesInputRef}
                    folderInputRef={folderInputRef}
                    selectedFiles={selectedFiles}
                    selectionSummary={selectionSummary}
                    onSelection={handleSelection}
                    limits={limits}
                    currentTotalBytes={currentTotalBytes}
                />

                <SettingsPanel
                    outputFormat={outputFormat}
                    quality={quality}
                    maxWidth={maxWidth}
                    maxHeight={maxHeight}
                    selectedCount={selectedUploadFiles.length}
                    isProcessing={isProcessing}
                    onOutputFormatChange={setOutputFormat}
                    onQualityChange={setQuality}
                    onMaxWidthChange={setMaxWidth}
                    onMaxHeightChange={setMaxHeight}
                    onOptimize={async () => {
                        const wasSuccessful = await handleOptimize({
                            files: selectedUploadFiles,
                            outputFormat,
                            quality,
                            maxWidth,
                            maxHeight,
                        });

                        if (wasSuccessful) {
                            resetSelectionState();
                            resetFileInputs();
                        }
                    }}
                />
            </section>

            <ResultPanel
                result={result}
                imageComparisonPreview={imageComparisonPreview}
                comparisonPosition={comparisonPosition}
                outputFormat={outputFormat}
                onComparisonPositionChange={setComparisonPosition}
            />

            <FileList files={selectedFiles} />
        </main>
    );
}

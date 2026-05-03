import { useEffect, useRef, useState } from 'react';

import { CreatorCard } from './components/CreatorCard';
import { HeroSection } from './components/HeroSection';
import { SourcePanel } from './components/SourcePanel';
import { SettingsPanel } from './components/SettingsPanel';
import { ResultPanel } from './components/ResultPanel';
import { FileList } from './components/FileList';
import { OUTPUT_FORMAT, type OutputFormat } from './constants/outputFormat';
import { useBackendStatus } from './hooks/useBackendStatus';
import { useImageProcessing } from './hooks/useImageProcessing';
import { filterSystemFiles } from './utils/fileFilters';

// ─── Constants ───────────────────────────────────────────────────────────────────

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

type SelectionSource = 'files' | 'folder' | null;

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
    batchSelectionSummary: SelectionSummary | null;
}

export interface ProcessingError {
    type: 'error';
    code: string;
    hint: string | null;
    message: string;
    title: string;
}

export type ProcessingState = ProcessingResult | ProcessingError | null;

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

    const { apiStatus, limits, avifAvailable } = useBackendStatus();
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
    const [zipName, setZipName] = useState('');
    const [outputPrefix, setOutputPrefix] = useState('');
    const [outputSuffix, setOutputSuffix] = useState('');
    const [outputStem, setOutputStem] = useState('');
    const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
    const [selectedUploadFiles, setSelectedUploadFiles] = useState<File[]>([]);
    const [selectionSummary, setSelectionSummary] = useState<SelectionSummary | null>(null);
    const [selectionSource, setSelectionSource] = useState<SelectionSource>(null);

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
        setSelectionSource(null);
    };

    const clearSelection = () => {
        resetSelectionState();
        clearResult();
        resetFileInputs();
    };

    const handleSelection = (files: FileList | File[] | null, source: Exclude<SelectionSource, null>) => {
        if (!files) {
            clearSelection();
            return;
        }

        setSelectionSource(source);

        // 1. Filter junk/system files FIRST (before format validation)
        const fileList = Array.isArray(files) ? files : Array.from(files);
        const filterResult = filterSystemFiles(fileList);
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
                    zipName={zipName}
                    outputPrefix={outputPrefix}
                    outputSuffix={outputSuffix}
                    outputStem={outputStem}
                    selectedCount={selectedUploadFiles.length}
                    showZipName={selectedUploadFiles.length > 1 || selectionSource === 'folder'}
                    showOutputStem={selectedUploadFiles.length > 1 || selectionSource === 'folder'}
                    isProcessing={isProcessing}
                    avifAvailable={avifAvailable}
                    onOutputFormatChange={setOutputFormat}
                    onQualityChange={setQuality}
                    onMaxWidthChange={setMaxWidth}
                    onMaxHeightChange={setMaxHeight}
                    onZipNameChange={setZipName}
                    onOutputPrefixChange={setOutputPrefix}
                    onOutputSuffixChange={setOutputSuffix}
                    onOutputStemChange={setOutputStem}
                    onOptimize={async () => {
                        const wasSuccessful = await handleOptimize({
                            files: selectedUploadFiles,
                            outputFormat,
                            quality,
                            maxWidth,
                            maxHeight,
                            zipName: zipName || undefined,
                            outputPrefix: outputPrefix || undefined,
                            outputSuffix: outputSuffix || undefined,
                            outputStem: outputStem || undefined,
                            selectionSummary: selectionSummary ?? undefined,
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
                batchSelectionSummary={selectionSummary}
            />

            <FileList files={selectedFiles} />

            <CreatorCard />
        </main>
    );
}

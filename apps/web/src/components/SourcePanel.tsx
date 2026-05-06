import { useState, type RefObject } from 'react';

import type { SelectedFile, SelectionSummary } from '../App';
import { computeBatchWarnings } from '../utils/batchWarnings';
import { formatBytesMB } from '../utils/formatters';

interface SourcePanelProps {
  filesInputRef: RefObject<HTMLInputElement | null>;
  folderInputRef: RefObject<HTMLInputElement | null>;
  selectedFiles: SelectedFile[];
  selectionSummary: SelectionSummary | null;
  onSelection: (files: FileList | File[] | null, source: 'files' | 'folder') => void;
  limits: { max_files: number; max_total_bytes: number };
  currentTotalBytes: number;
}

const INPUT_ACCEPT = '.jpg,.jpeg,.png,.webp';
type PickerFile = File & { webkitRelativePath?: string };
type DirectoryHandleWithValues = FileSystemDirectoryHandle & {
  values: () => AsyncIterable<FileSystemHandle>;
};

function isFileHandle(entry: FileSystemHandle): entry is FileSystemFileHandle {
  return entry.kind === 'file';
}

function isDirectoryHandle(entry: FileSystemHandle): entry is FileSystemDirectoryHandle {
  return entry.kind === 'directory';
}

async function collectDirectoryFiles(
  directoryHandle: FileSystemDirectoryHandle,
  currentPath = directoryHandle.name,
): Promise<PickerFile[]> {
  const files: PickerFile[] = [];
  const iterableDirectoryHandle = directoryHandle as DirectoryHandleWithValues;

  for await (const entry of iterableDirectoryHandle.values()) {
    const entryPath = `${currentPath}/${entry.name}`;

    if (isFileHandle(entry)) {
      const file = (await entry.getFile()) as PickerFile;
      Object.defineProperty(file, 'webkitRelativePath', {
        value: entryPath,
        configurable: true,
      });
      files.push(file);
      continue;
    }

    if (isDirectoryHandle(entry)) {
      files.push(...(await collectDirectoryFiles(entry, entryPath)));
    }
  }

  return files;
}

export function SourcePanel({
  filesInputRef,
  folderInputRef,
  selectedFiles,
  selectionSummary,
  onSelection,
  limits,
  currentTotalBytes,
}: SourcePanelProps) {
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);

  const totalSizeLabel = formatBytesMB(
    selectedFiles.reduce((acc, f) => acc + f.sizeInBytes, 0) || null,
  );

  const isOverFileLimit = selectedFiles.length > limits.max_files;
  const isOverSizeLimit = currentTotalBytes > limits.max_total_bytes;

  const cautionWarnings = computeBatchWarnings(selectedFiles.length, currentTotalBytes, limits);

  const handleFolderConfirm = async () => {
    setIsFolderModalOpen(false);

    const directoryWindow = window as Window & {
      showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
    };

    if (typeof directoryWindow.showDirectoryPicker === 'function') {
      try {
        const directoryHandle = await directoryWindow.showDirectoryPicker();
        const files = await collectDirectoryFiles(directoryHandle);
        onSelection(files, 'folder');
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return;
        }
      }
    }

    folderInputRef.current?.click();
  };

  return (
    <div className="column">
      <h2>Source assets</h2>

      <label className="picker">
        <span>Select files</span>
        <button
          type="button"
          className="folder-picker-button"
          onClick={() => filesInputRef.current?.click()}
        >
          Choose files
        </button>
        <input
          ref={filesInputRef}
          accept={INPUT_ACCEPT}
          multiple
          type="file"
          className="folder-input-hidden"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => onSelection(event.target.files, 'files')}
        />
        <small className="format-hint">Supported input formats: JPG, JPEG, PNG, WEBP.</small>
      </label>

      <label className="picker">
        <span>Select folder</span>
        <button
          type="button"
          className="folder-picker-button"
          onClick={() => setIsFolderModalOpen(true)}
        >
          Choose folder
        </button>
        <input
          ref={folderInputRef}
          accept={INPUT_ACCEPT}
          multiple
          type="file"
          webkitdirectory=""
          directory=""
          className="folder-input-hidden"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => onSelection(event.target.files, 'folder')}
        />
        <small className="format-hint">
          Folder uploads can include only JPG, JPEG, PNG, and WEBP files.
        </small>
      </label>

      {isFolderModalOpen && (
        <div className="app-modal-backdrop" role="presentation" onClick={() => setIsFolderModalOpen(false)}>
          <div
            className="app-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="folder-modal-title"
            aria-describedby="folder-modal-description"
            onClick={(event) => event.stopPropagation()}
          >
            <p className="app-modal-eyebrow">Folder upload</p>
            <h3 id="folder-modal-title">Choose a folder for batch processing</h3>
            <p id="folder-modal-description" className="app-modal-description">
              We’ll open your browser’s native folder picker next. Select only folders you trust and
              that contain JPG, JPEG, PNG, or WEBP files.
            </p>
            <div className="app-modal-actions">
              <button type="button" className="modal-secondary-button" onClick={() => setIsFolderModalOpen(false)}>
                Cancel
              </button>
              <button type="button" className="primary-button" onClick={handleFolderConfirm}>
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {cautionWarnings.map((warning) => (
        <div key={warning.message} className="batch-warning caution-warning">
          {warning.message}
        </div>
      ))}

      {(isOverFileLimit || isOverSizeLimit) && (
        <div className="selection-warning limits-warning">
          <span>
            Limits exceeded: {isOverFileLimit && `${selectedFiles.length}/${limits.max_files} files`}
            {isOverFileLimit && isOverSizeLimit && ' · '}
            {isOverSizeLimit && `${totalSizeLabel}/${formatBytesMB(limits.max_total_bytes)} total`}
          </span>
        </div>
      )}

      <div className="summary-box">
        <strong>{selectedFiles.length}</strong>
        <span> file{selectedFiles.length !== 1 ? 's' : ''} selected</span>
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
  );
}

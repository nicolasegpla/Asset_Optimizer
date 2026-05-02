import type { SelectedFile, SelectionSummary } from '../App';
import { computeBatchWarnings } from '../utils/batchWarnings';
import { formatBytesMB } from '../utils/formatters';

interface SourcePanelProps {
  filesInputRef: React.RefObject<HTMLInputElement | null>;
  folderInputRef: React.RefObject<HTMLInputElement | null>;
  selectedFiles: SelectedFile[];
  selectionSummary: SelectionSummary | null;
  onSelection: (files: FileList | null) => void;
  limits: { max_files: number; max_total_bytes: number };
  currentTotalBytes: number;
}

const INPUT_ACCEPT = '.jpg,.jpeg,.png,.webp';

export function SourcePanel({
  filesInputRef,
  folderInputRef,
  selectedFiles,
  selectionSummary,
  onSelection,
  limits,
  currentTotalBytes,
}: SourcePanelProps) {
  const totalSizeLabel = formatBytesMB(
    selectedFiles.reduce((acc, f) => acc + f.sizeInBytes, 0) || null,
  );

  const isOverFileLimit = selectedFiles.length > limits.max_files;
  const isOverSizeLimit = currentTotalBytes > limits.max_total_bytes;

  const cautionWarnings = computeBatchWarnings(selectedFiles.length, currentTotalBytes, limits);

  return (
    <div className="column">
      <h2>Source assets</h2>

      <label className="picker">
        <span>Select files</span>
        <input
          ref={filesInputRef}
          accept={INPUT_ACCEPT}
          multiple
          type="file"
          onChange={(event) => onSelection(event.target.files)}
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
          onChange={(event) => onSelection(event.target.files)}
        />
        <small className="format-hint">
          Folder uploads can include only JPG, JPEG, PNG, and WEBP files.
        </small>
      </label>

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
  );
}

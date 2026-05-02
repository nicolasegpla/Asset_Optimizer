/**
 * Batch result summary panel — shown when processedCount > 1.
 * Displays: processed/failed counts, total savings, per-file table via BatchFileList.
 */
import type { BatchManifest } from '../utils/batchManifest';
import { formatBytes } from '../utils/formatters';
import { computeSavingsPercent } from '../utils/batchManifest';
import { BatchFileList } from './BatchFileList';

interface BatchResultPanelProps {
  manifest: BatchManifest;
  errorCount: number;
  downloadedFileName: string | null;
}

export function BatchResultPanel({ manifest, errorCount, downloadedFileName }: BatchResultPanelProps) {
  const { summary, files, errors } = manifest;
  const savingsPct = computeSavingsPercent(summary.totalOriginalBytes, summary.totalOptimizedBytes);

  const headerText =
    errorCount > 0
      ? `${summary.processedFiles} of ${summary.totalFiles} files processed successfully`
      : `${summary.processedFiles} files processed successfully`;

  return (
    <div className="batch-result-panel">
      <h3>{headerText}</h3>

      {downloadedFileName && (
        <p className="batch-download-confirmation">
          Downloaded: <strong>{downloadedFileName}</strong>
        </p>
      )}

      <p className="batch-savings-summary">
        Original: {formatBytes(summary.totalOriginalBytes)} → Optimized: {formatBytes(summary.totalOptimizedBytes)}
        {summary.totalOriginalBytes > 0 && (
          <span className="ratio-badge">-{savingsPct}%</span>
        )}
      </p>

      {files.length > 0 && (
        <BatchFileList files={files} errors={errors} />
      )}

      {errors.length > 0 && (
        <div className="batch-errors-section">
          <h4>Failed files ({errors.length})</h4>
          <ul className="batch-error-list">
            {errors.map((err) => (
              <li key={err.source} className="batch-error-item">
                <span className="batch-error-name">{err.source}</span>
                <span className="batch-error-msg">{err.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
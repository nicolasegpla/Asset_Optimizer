/**
 * Batch result summary panel — shown when processedCount > 1.
 * Displays: tabs (All/Success/Failed), skipped banner, per-file table via BatchFileList,
 * and manifest actions.
 */
import { useState, useMemo } from 'react';
import type { BatchManifest } from '../utils/batchManifest';
import { formatBytes } from '../utils/formatters';
import { computeSavingsPercent } from '../utils/batchManifest';
import {
  normalizeBatchRows,
  filterByTab,
  sortRows,
  formatBatchSummaryText,
  type BatchTab,
  type SortKey,
  type SortDir,
  type BatchResultRow,
  type BatchSelectionSummary,
} from '../utils/batchResultRows';
import { BatchFileList } from './BatchFileList';
import { ManifestActions } from './ManifestActions';

interface BatchResultPanelProps {
  manifest: BatchManifest;
  errorCount: number;
  downloadedFileName: string | null;
  batchSelectionSummary: BatchSelectionSummary | null;
}

const TABS: { key: BatchTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'success', label: 'Success' },
  { key: 'failed', label: 'Failed' },
];

export function BatchResultPanel({
  manifest,
  errorCount,
  downloadedFileName,
  batchSelectionSummary,
}: BatchResultPanelProps) {
  const [activeTab, setActiveTab] = useState<BatchTab>('all');
  const [sortKey, setSortKey] = useState<SortKey>('savings');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const allRows = useMemo(() => normalizeBatchRows(manifest), [manifest]);
  const tabRows = useMemo(() => filterByTab(allRows, activeTab), [allRows, activeTab]);
  const sortedRows = useMemo(() => sortRows(tabRows, sortKey, sortDir), [tabRows, sortKey, sortDir]);

  const successCount = allRows.filter((r) => r.status === 'success').length;
  const failedCount = allRows.filter((r) => r.status === 'failed').length;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const savingsPct = computeSavingsPercent(manifest.summary.totalOriginalBytes, manifest.summary.totalOptimizedBytes);

  const headerText =
    errorCount > 0
      ? `${manifest.summary.processedFiles} of ${manifest.summary.totalFiles} files processed successfully`
      : `${manifest.summary.processedFiles} files processed successfully`;

  const skippedCount = batchSelectionSummary?.skippedCount ?? 0;
  const skippedNames = batchSelectionSummary?.invalidFileNames ?? [];

  return (
    <div className="batch-result-panel">
      <h3>{headerText}</h3>

      {downloadedFileName && (
        <p className="batch-download-confirmation">
          Downloaded: <strong>{downloadedFileName}</strong>
        </p>
      )}

      <p className="batch-savings-summary">
        Original: {formatBytes(manifest.summary.totalOriginalBytes)} → Optimized:{' '}
        {formatBytes(manifest.summary.totalOptimizedBytes)}
        {manifest.summary.totalOriginalBytes > 0 && (
          <span className="ratio-badge">-{savingsPct}%</span>
        )}
      </p>

      {skippedCount > 0 && (
        <div className="skipped-banner">
          <span className="skipped-icon">⚠</span>
          <span>
            {skippedCount} file(s) skipped before upload: {skippedNames.slice(0, 3).join(', ')}
            {skippedCount > 3 ? ` +${skippedCount - 3} more` : ''}
          </span>
        </div>
      )}

      <div className="batch-tabs" role="tablist">
        {TABS.map(({ key, label }) => {
          const count = key === 'all' ? allRows.length : key === 'success' ? successCount : failedCount;
          return (
            <button
              key={key}
              role="tab"
              type="button"
              aria-selected={activeTab === key}
              className={`batch-tab ${activeTab === key ? 'batch-tab-active' : ''}`}
              onClick={() => setActiveTab(key)}
            >
              {label} ({count})
            </button>
          );
        })}
      </div>

      {sortedRows.length === 0 ? (
        <div className="batch-empty-state">
          {activeTab === 'all'
            ? 'No files were processed.'
            : activeTab === 'success'
              ? 'No files succeeded.'
              : 'No files failed.'}
        </div>
      ) : (
        <BatchFileList rows={sortedRows} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
      )}

      <ManifestActions
        manifest={manifest}
        selectionSummary={batchSelectionSummary}
      />
    </div>
  );
}

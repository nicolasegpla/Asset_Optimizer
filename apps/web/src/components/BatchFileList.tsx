/**
 * Sortable per-file table for batch results.
 * Controlled component — receives rows + sort state from BatchResultPanel.
 * Renders both success and failed row variants.
 */
import type { BatchResultRow, SortKey, SortDir } from '../utils/batchResultRows';
import { formatBytes, formatDimensions } from '../utils/formatters';

interface BatchFileListProps {
  rows: BatchResultRow[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
}

function savingsPct(row: BatchResultRow): number {
  if (row.status === 'failed' || row.originalBytes === 0) return 0;
  return Math.round(((row.originalBytes - row.optimizedBytes) / row.originalBytes) * 100);
}

function SortIcon({ column }: { column: SortKey }) {
  // Icons are visual; actual sort direction shown via text arrow in button
  return null;
}

export function BatchFileList({ rows, sortKey, sortDir, onSort }: BatchFileListProps) {
  return (
    <div className="batch-file-list">
      <table>
        <thead>
          <tr>
            <th>
              <button type="button" className="sort-btn" onClick={() => onSort('name')}>
                Filename
                {sortKey === 'name' && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </button>
            </th>
            <th>
              <button type="button" className="sort-btn" onClick={() => onSort('originalSize')}>
                Original size
                {sortKey === 'originalSize' && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </button>
            </th>
            <th>Optimized size</th>
            <th>
              <button type="button" className="sort-btn" onClick={() => onSort('savings')}>
                Savings
                {sortKey === 'savings' && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </button>
            </th>
            <th>
              <button type="button" className="sort-btn" onClick={() => onSort('format')}>
                Format change
                {sortKey === 'format' && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </button>
            </th>
            <th>
              <button type="button" className="sort-btn" onClick={() => onSort('dimensions')}>
                Dimensions
                {sortKey === 'dimensions' && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            if (row.status === 'success') {
              const savings = savingsPct(row);
              const formatChange = row.outputFormat.toUpperCase();

              return (
                <tr key={row.source} className="batch-row batch-row-success">
                  <td className="file-name-cell">{row.source}</td>
                  <td>{formatBytes(row.originalBytes)}</td>
                  <td>{formatBytes(row.optimizedBytes)}</td>
                  <td>
                    <span className="savings-badge">-{savings}%</span>
                  </td>
                  <td>{formatChange}</td>
                  <td>
                    {formatDimensions(row.originalDimensions.width, row.originalDimensions.height)} →{' '}
                    {formatDimensions(row.outputDimensions.width, row.outputDimensions.height)}
                  </td>
                </tr>
              );
            } else {
              // Failed row — error renders inline
              return (
                <tr key={row.source} className="batch-row batch-row-failed">
                  <td className="file-name-cell">{row.source}</td>
                  <td className="batch-cell-na">—</td>
                  <td className="batch-cell-na">—</td>
                  <td className="batch-cell-na">—</td>
                  <td className="batch-cell-na">—</td>
                  <td className="batch-error-cell">
                    <span className="batch-error-code">[{row.errorCode}]</span>{' '}
                    <span className="batch-error-msg">{row.errorMessage}</span>
                  </td>
                </tr>
              );
            }
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Sortable per-file table for batch results.
 * Default sort: savings % descending. Toggle: alphabetical by source name.
 */
import { useState } from 'react';
import type { BatchManifestFile, BatchManifestError } from '../utils/batchManifest';
import { formatBytes, formatDimensions } from '../utils/formatters';

interface BatchFileListProps {
  files: BatchManifestFile[];
  errors: BatchManifestError[];
}

type SortKey = "savings" | "name";
type SortDir = "asc" | "desc";

export function BatchFileList({ files, errors }: BatchFileListProps) {
  const [sortKey, setSortKey] = useState<SortKey>("savings");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedFiles = [...files].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "savings") {
      const savingsA = (a.originalBytes - a.optimizedBytes) / a.originalBytes;
      const savingsB = (b.originalBytes - b.optimizedBytes) / b.originalBytes;
      cmp = savingsA - savingsB;
    } else {
      cmp = a.source.localeCompare(b.source);
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <div className="batch-file-list">
      <table>
        <thead>
          <tr>
            <th>
              <button type="button" onClick={() => handleSort("name")}>
                Filename
                {sortKey === "name" && (sortDir === "asc" ? " ↑" : " ↓")}
              </button>
            </th>
            <th>Original size</th>
            <th>Optimized size</th>
            <th>
              <button type="button" onClick={() => handleSort("savings")}>
                Savings
                {sortKey === "savings" && (sortDir === "asc" ? " ↑" : " ↓")}
              </button>
            </th>
            <th>Format change</th>
            <th>Dimensions</th>
          </tr>
        </thead>
        <tbody>
          {sortedFiles.map((file) => {
            const savingsPct = Math.round(
              ((file.originalBytes - file.optimizedBytes) / file.originalBytes) * 100,
            );
            const formatChange =
              file.originalFormat.toUpperCase() !== file.outputFormat.toUpperCase()
                ? `${file.originalFormat.toUpperCase()} → ${file.outputFormat.toUpperCase()}`
                : `${file.originalFormat.toUpperCase()}`;

            return (
              <tr key={file.source}>
                <td className="file-name-cell">{file.source}</td>
                <td>{formatBytes(file.originalBytes)}</td>
                <td>{formatBytes(file.optimizedBytes)}</td>
                <td>
                  <span className="savings-badge">-{savingsPct}%</span>
                </td>
                <td>{formatChange}</td>
                <td>
                  {formatDimensions(file.originalDimensions.width, file.originalDimensions.height)} →{' '}
                  {formatDimensions(file.outputDimensions.width, file.outputDimensions.height)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
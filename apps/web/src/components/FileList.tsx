import { useState } from 'react';
import type { SelectedFile } from '../App';

interface FileListProps {
  files: SelectedFile[];
}

const PREVIEW_COUNT = 8;

export function FileList({ files }: FileListProps) {
  // Reset to collapsed whenever the files prop changes (new selection)
  const [expanded, setExpanded] = useState(false);

  const showToggle = files.length > PREVIEW_COUNT;
  const visibleFiles = expanded ? files : files.slice(0, PREVIEW_COUNT);

  return (
    <section className="card">
      <h2>Current batch preview</h2>
      {files.length === 0 ? (
        <p className="empty-state">No files selected yet.</p>
      ) : (
        <>
          <ul className="file-list">
            {visibleFiles.map((file) => (
              <li key={file.relativePath}>
                <span>{file.relativePath}</span>
                <strong>{Math.round(file.sizeInBytes / 1024)} KB</strong>
              </li>
            ))}
          </ul>
          {showToggle && (
            <button
              className="file-list-toggle"
              onClick={() => setExpanded((prev) => !prev)}
              type="button"
            >
              {expanded
                ? 'Show less'
                : `Show all ${files.length} files`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
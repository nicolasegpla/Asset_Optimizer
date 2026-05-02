import type { SelectedFile } from '../App';

interface FileListProps {
  files: SelectedFile[];
}

export function FileList({ files }: FileListProps) {
  return (
    <section className="card">
      <h2>Current batch preview</h2>
      {files.length === 0 ? (
        <p className="empty-state">No files selected yet.</p>
      ) : (
        <ul className="file-list">
          {files.slice(0, 8).map((file) => (
            <li key={file.relativePath}>
              <span>{file.relativePath}</span>
              <strong>{Math.round(file.sizeInBytes / 1024)} KB</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
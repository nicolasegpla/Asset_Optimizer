import type { ProcessingState, ImageComparisonPreview } from '../App';
import type { OutputFormat } from '../App';
import { formatBytes, formatDimensions } from '../utils/formatters';

interface ResultPanelProps {
  result: ProcessingState;
  imageComparisonPreview: ImageComparisonPreview | null;
  comparisonPosition: number;
  outputFormat: OutputFormat;
  onComparisonPositionChange: (position: number) => void;
}

export function ResultPanel({
  result,
  imageComparisonPreview,
  comparisonPosition,
  outputFormat,
  onComparisonPositionChange,
}: ResultPanelProps) {
  if (!result) return null;

  if (result.type === 'error') {
    return (
      <section className="card error-card">
        <h2>{result.title}</h2>
        <p className="error-message">{result.message}</p>
        {result.hint && <p className="error-hint">{result.hint}</p>}
        <p className="error-code">Code: {result.code}</p>
      </section>
    );
  }

  return (
    <section className="card result-card">
      <h2>Result</h2>
      {result.processedCount === 1 ? (
        <div className="result-summary">
          <p>
            <strong>{result.downloadedFileName}</strong> downloaded successfully.
          </p>
          <div className="size-comparison">
            <span>Original: {formatBytes(result.originalBytes)}</span>
            <span>→</span>
            <span>Optimized: {formatBytes(result.optimizedBytes)}</span>
            <span className="ratio-badge">
              {result.compressionRatio !== null ? `-${result.compressionRatio.toFixed(1)}%` : '—'}
            </span>
          </div>
          {imageComparisonPreview && (
            <div className="comparison-panel">
              <div className="comparison-labels">
                <span>Before</span>
                <span>After</span>
              </div>

              <div className="comparison-stage">
                <img
                  className="comparison-image"
                  src={imageComparisonPreview.originalUrl}
                  alt={`Original ${imageComparisonPreview.originalName}`}
                />
                <div
                  className="comparison-overlay"
                  style={{ clipPath: `inset(0 0 0 ${comparisonPosition}%)` }}
                >
                  <img
                    className="comparison-image comparison-image-overlay"
                    src={imageComparisonPreview.optimizedUrl}
                    alt={`Optimized ${result.downloadedFileName ?? 'image'}`}
                  />
                </div>
                <div className="comparison-divider" style={{ left: `${comparisonPosition}%` }} />
              </div>

              <label className="comparison-slider">
                <span>Comparison slider: {comparisonPosition}%</span>
                <input
                  min={0}
                  max={100}
                  step={1}
                  type="range"
                  value={comparisonPosition}
                  onChange={(event) => onComparisonPositionChange(Number(event.target.value))}
                />
              </label>

              <div className="comparison-caption">
                <span>
                  {imageComparisonPreview.originalName} ·{' '}
                  {(result.originalFormat ?? 'unknown').toUpperCase()} ·{' '}
                  {formatDimensions(result.originalWidth, result.originalHeight)}
                </span>
                <span>
                  {(result.downloadedFileName ?? 'optimized image')} ·{' '}
                  {(result.outputFormat ?? outputFormat).toUpperCase()} ·{' '}
                  {formatDimensions(result.outputWidth, result.outputHeight)}
                </span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="result-summary">
          <p>
            <strong>{result.processedCount} files</strong> packaged into{' '}
            <strong>{result.downloadedFileName}</strong>.
          </p>
          <div className="size-comparison">
            <span>Original: {formatBytes(result.originalBytes)}</span>
            <span>→</span>
            <span>Optimized: {formatBytes(result.optimizedBytes)}</span>
          </div>
        </div>
      )}
    </section>
  );
}
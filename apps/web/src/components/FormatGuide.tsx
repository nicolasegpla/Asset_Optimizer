/**
 * FormatGuide — collapsible format guidance disclosure.
 * Shows best-for, transparency, browser support, and cautions for the selected format.
 */
import { FORMAT_CATALOG } from '../constants/formatCatalog';
import type { OutputFormat } from '../constants/outputFormat';

interface FormatGuideProps {
  outputFormat: OutputFormat;
}

function BrowserSupportLabel({ level }: { level: string }) {
  const map: Record<string, string> = {
    wide: 'All modern browsers',
    modern: 'All modern browsers',
    emerging: 'Growing support — check audience',
  };
  return <span>{map[level] ?? level}</span>;
}

function SupportBadge({ supported }: { supported: boolean }) {
  return supported ? (
    <span className="format-guide-badge format-guide-badge--supported">Transparency ✦</span>
  ) : (
    <span className="format-guide-badge format-guide-badge--unsupported">No transparency</span>
  );
}

export function FormatGuide({ outputFormat }: FormatGuideProps) {
  const entry = FORMAT_CATALOG[outputFormat];

  return (
    <details className="format-guide">
      <summary className="format-guide-summary">
        Format guidance: {entry.displayName}
      </summary>
      <div className="format-guide-body">
        <p className="format-guide-best-for">
          <strong>Best for:</strong> {entry.bestFor}
        </p>
        <div className="format-guide-meta">
          <SupportBadge supported={entry.supportsTransparency} />
          <span className="format-guide-browser-support">
            <strong>Browser support:</strong> <BrowserSupportLabel level={entry.browserSupport} />
          </span>
        </div>
        {entry.cautions.length > 0 && (
          <ul className="format-guide-cautions">
            {entry.cautions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

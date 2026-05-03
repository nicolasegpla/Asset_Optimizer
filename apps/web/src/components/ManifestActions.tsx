/**
 * Manifest download + clipboard copy actions for BatchResultPanel.
 */
import { useCallback, useRef, useState } from 'react';
import type { BatchManifest } from '../utils/batchManifest';
import { formatBatchSummaryText, type BatchSelectionSummary } from '../utils/batchResultRows';

interface ManifestActionsProps {
  manifest: BatchManifest;
  selectionSummary: BatchSelectionSummary | null;
}

const COPY_FEEDBACK_DURATION_MS = 2000;

export function ManifestActions({ manifest, selectionSummary }: ManifestActionsProps) {
  const [copied, setCopied] = useState(false);
  const feedbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCopy = useCallback(async () => {
    const text = formatBatchSummaryText(manifest, selectionSummary);

    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API unavailable — fall back to textarea selection
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }

    setCopied(true);
    if (feedbackTimerRef.current !== null) {
      clearTimeout(feedbackTimerRef.current);
    }
    feedbackTimerRef.current = setTimeout(() => setCopied(false), COPY_FEEDBACK_DURATION_MS);
  }, [manifest, selectionSummary]);

  const handleDownload = useCallback(() => {
    const now = new Date();
    const iso = now.toISOString().slice(0, 10); // YYYY-MM-DD
    const filename = `manifest-${iso}.json`;

    const json = JSON.stringify(manifest, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [manifest]);

  return (
    <div className="manifest-actions">
      <button type="button" className="manifest-action-btn" onClick={handleDownload}>
        Download manifest
      </button>
      <button type="button" className="manifest-action-btn" onClick={handleCopy}>
        {copied ? 'Copied!' : 'Copy summary'}
      </button>
    </div>
  );
}

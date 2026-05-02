/**
 * Vitest + jsdom setup for Asset Optimizer frontend tests.
 *
 * Provides DOM environment mocks for URL.createObjectURL / revokeObjectURL
 * and stubs anchor click behavior for download flows.
 */

import { afterEach, beforeEach, vi } from 'vitest';

// ─── URL.createObjectURL mock ────────────────────────────────────────────────

const objectUrlStore = new Map<string, Blob>();

beforeEach(() => {
  objectUrlStore.clear();
  globalThis.URL.createObjectURL = (blob: Blob): string => {
    const url = `blob:${Date.now()}-${Math.random().toString(36).slice(2)}`;
    objectUrlStore.set(url, blob);
    return url;
  };

  globalThis.URL.revokeObjectURL = (url: string): void => {
    objectUrlStore.delete(url);
  };
});

afterEach(() => {
  objectUrlStore.clear();
  vi.restoreAllMocks();
});

// ─── Anchor click stub (no actual navigation) ────────────────────────────────

const kAnchorClickCleanup: Array<() => void> = [];

beforeEach(() => {
  kAnchorClickCleanup.length = 0;
});

afterEach(() => {
  for (const cleanup of kAnchorClickCleanup) {
    cleanup();
  }
  kAnchorClickCleanup.length = 0;
});

/**
 * Intercept `<a>` click events to prevent actual navigation while still
 * supporting download flow assertions (href, download attr present).
 * Install in each test via `installAnchorClickStub()`.
 */
export function installAnchorClickStub(): () => void {
  const events: Array<MouseEvent> = [];

  const handler = (event: MouseEvent) => {
    const anchor = event.target as HTMLAnchorElement | null;
    if (anchor?.tagName === 'A') {
      event.preventDefault();
      events.push(event);
    }
  };

  document.addEventListener('click', handler);

  const cleanup = () => {
    document.removeEventListener('click', handler);
    const idx = kAnchorClickCleanup.indexOf(cleanup);
    if (idx !== -1) kAnchorClickCleanup.splice(idx, 1);
  };

  kAnchorClickCleanup.push(cleanup);
  return cleanup;
}

// Export events array for assertions in tests
export { kAnchorClickCleanup as anchorClickEvents };

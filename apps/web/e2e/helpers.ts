/**
 * Shared Playwright fixture helpers for Asset Optimizer smoke tests.
 */
import { type Download, type Page, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const FIXTURES_DIR = path.join(__dirname, 'fixtures');

// ─── File helpers ────────────────────────────────────────────────────────────

/**
 * Returns the absolute path to a committed fixture file.
 */
export function fixturePath(name: string): string {
    return path.join(FIXTURES_DIR, name);
}

/**
 * Upload one or more files to a page's file input located by label text.
 * Returns the resolved file paths.
 */
export async function uploadFiles(
    page: Page,
    inputLabel: string,
    filePaths: string | string[],
): Promise<void> {
    const input = page.getByLabel(inputLabel).locator('..').locator('input[type="file"]');
    await input.setInputFiles(filePaths);
}

export async function expectSuggestedDownload(download: Download, expectedName: string): Promise<void> {
    await expect(download.suggestedFilename()).toBe(expectedName);
}

// ─── Result panel assertions ─────────────────────────────────────────────────

/**
 * Assert the single-file success result is visible in the Result panel.
 * Checks for:
 *   - the "Result" heading
 *   - a downloaded filename containing the expected stem
 *   - a size-comparison row (Original → Optimized)
 */
export async function assertSingleResult(page: Page, filenameStem?: string): Promise<void> {
    await expect(page.locator('section.result-card h2')).toHaveText('Result');
    const downloadedLine = page.locator('.result-summary p').first();
    await expect(downloadedLine).toContainText('downloaded successfully');
    if (filenameStem) {
        await expect(downloadedLine).toContainText(filenameStem);
    }
    // Size comparison row: "Original: X → Optimized: Y"
    await expect(page.locator('.size-comparison')).toBeVisible();
}

/**
 * Assert the batch/ZIP success result is visible in the Result panel.
 * Checks for:
 *   - the batch result panel heading
 *   - a ZIP downloaded filename confirmation
 *   - the batch tabs (All / Success / Failed) are rendered
 */
export async function assertBatchResult(page: Page, zipNameStem?: string): Promise<void> {
    await expect(page.locator('.batch-result-panel h3')).toBeVisible();
    const confirmation = page.locator('.batch-download-confirmation');
    await expect(confirmation).toBeVisible();
    if (zipNameStem) {
        await expect(confirmation).toContainText(zipNameStem);
    }
    // Tabs should be present
    await expect(page.locator('.batch-tabs')).toBeVisible();
}

// ─── Misc helpers ──────────────────────────────────────────────────────────────

/**
 * Wait for the optimize button to be enabled (not disabled, not processing).
 */
export async function waitForOptimizeReady(page: Page): Promise<void> {
    const optimizeButton = page.getByRole('button', { name: 'Optimize & Download' });
    await optimizeButton.waitFor({ state: 'visible' });
    await expect(optimizeButton).toBeEnabled();
}

/**
 * Asset Optimizer — browser smoke tests
 *
 * Covers the two highest-value happy paths:
 *   1. single file upload → optimize → direct download success result
 *   2. multiple files upload → optimize → ZIP/batch success result
 *
 * Target: local dev server (Vite on :5173) + API on :8000.
 * Run with: npm run test:e2e
 */
import { test, expect } from '@playwright/test';
import {
  fixturePath,
  assertSingleResult,
  assertBatchResult,
  waitForOptimizeReady,
  uploadFiles,
  expectSuggestedDownload,
} from './helpers';

// ─── Fixtures ────────────────────────────────────────────────────────────────────

/** A minimal valid JPEG fixture (single file – single-file path). */
const SINGLE_FIXTURE = fixturePath('fixture-smoke.jpg');

/** Two minimal valid JPEG fixtures (batch path). */
const BATCH_FIXTURES = [
    fixturePath('fixture-smoke-a.jpg'),
    fixturePath('fixture-smoke-b.jpg'),
];

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('smoke', () => {

    test('single file upload → optimize → direct download success', async ({ page }) => {
        // 1. Navigate to app
        await page.goto('/');

        // 2. Wait for the app to be ready (API online badge)
        await expect(page.getByText('API: online')).toBeVisible({ timeout: 10_000 });

        // 3. Upload single fixture file via the "files" input
        await uploadFiles(page, 'Select files', SINGLE_FIXTURE);

        // 4. Wait for the file count to update in the summary box
        await expect(page.getByText('1 file selected')).toBeVisible();

        // 5. Verify optimize button is enabled
        await waitForOptimizeReady(page);

        // 6. Click Optimize & Download
        const downloadPromise = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Optimize & Download' }).click();
        const download = await downloadPromise;
        await expectSuggestedDownload(download, 'fixture-smoke.webp');

        // 7. Assert single-file success result is shown
        await assertSingleResult(page, 'fixture-smoke');

        // 8. Assert comparison panel is visible (before/after slider)
        await expect(page.locator('.comparison-panel')).toBeVisible();
    });

    test('multiple files upload → optimize → ZIP/batch success result', async ({ page }) => {
        // 1. Navigate to app
        await page.goto('/');

        // 2. Wait for API to be online
        await expect(page.getByText('API: online')).toBeVisible({ timeout: 10_000 });

        // 3. Upload two fixture files via the "files" input (multi-file select)
        await uploadFiles(page, 'Select files', BATCH_FIXTURES);

        // 4. Wait for the file count to update
        await expect(page.getByText('2 files selected')).toBeVisible();

        // 5. Verify optimize button is enabled
        await waitForOptimizeReady(page);

        // 6. Click Optimize & Download
        const downloadPromise = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Optimize & Download' }).click();
        const download = await downloadPromise;
        await expectSuggestedDownload(download, 'optimized-assets.zip');

        // 7. Assert batch/ZIP success result is shown
        await assertBatchResult(page, 'optimized-assets');

        // 8. Assert batch tabs are rendered (All / Success / Failed)
        await expect(page.locator('.batch-tabs')).toBeVisible();
    });

});

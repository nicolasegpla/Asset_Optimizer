# Asset Optimizer 1.0.0 Contract

This document is the **frozen product contract** for Asset Optimizer `1.0.0`.

Use it as the baseline before adding new improvements, changing UX, or evolving the API. If future work changes any rule here, that change should be treated as an intentional product decision, not as accidental drift.

## Quick path

1. Read the **Current Contract** section before planning changes.
2. Check **Non-goals / not promised** so you do not assume missing capabilities already exist.
3. When changing behavior, update this document together with code and tests.

## Current Contract

| Area | 1.0.0 decision |
|------|----------------|
| Input formats | `jpg`, `jpeg`, `png`, `webp` |
| Output formats | `jpg`, `png`, `webp`, `avif` |
| Processing model | Synchronous |
| Single file result | Direct file download |
| Multi-file / folder result | ZIP download |
| Folder handling | Preserve relative paths when available |
| Batch metadata | `manifest.json` included in ZIP |
| Partial success | Supported |
| AVIF availability | Runtime-dependent, exposed by `/api/v1/capabilities` |
| Main frontend/backend limits | 100 files, 50 MB total, 50 MP per image |

## Product Promise

Asset Optimizer is not just a format converter.

At `1.0.0`, the stable promise is:

> Prepare web-ready image assets with reliable conversion, compression, resize, naming, and batch packaging behavior.

That means this version is expected to behave consistently for the common workflows below.

## Stable User Flows

### 1. Single file optimization

- User uploads one supported image.
- User chooses output format, quality, and optional dimensions.
- App returns a direct file download.
- Result UI shows original vs optimized size and, when possible, before/after comparison.

### 2. Multi-file batch optimization

- User uploads two or more supported files.
- App returns a ZIP file.
- ZIP includes transformed files plus `manifest.json`.
- Result UI shows batch summary, processed files, and manifest actions.

### 3. Folder optimization

- User selects a folder from the browser.
- Supported files inside the folder are processed.
- Relative structure is preserved in the ZIP when the browser/runtime provides path information.
- ZIP naming is separate from internal output naming.

### 4. Partial success

- Invalid or failed files do not block valid files from returning.
- Pre-upload unsupported files can be skipped before upload.
- Backend processing failures appear in the manifest `errors` array.
- Result summary distinguishes processed output from failures/skips.

## Formats and AVIF Rules

### Supported input

- `JPG / JPEG`
- `PNG`
- `WEBP`

### Supported output

- `JPG / JPEG`
- `PNG`
- `WEBP`
- `AVIF`

### AVIF contract

- AVIF support is **runtime-dependent**, not assumed blindly.
- The backend validates AVIF capability at startup.
- `/api/v1/capabilities` exposes whether AVIF is available.
- The frontend should not advertise AVIF as available without backend confirmation.
- If AVIF is unavailable in a given runtime, the backend remains the final authority.

### JPG transparency rule

- If a transparent source is exported to JPG, transparency is composited onto white.

## Naming Contract

### Single file

- Keeps the original basename.
- Optional prefix and suffix can be applied.
- File extension changes to match the selected output format.

### Batch / folder

- Internal output names use sequential naming.
- Batch/folder output can replace basenames using `output_stem-N` behavior.
- ZIP file name is configured separately from internal file names.

### Collision handling

- ZIP outputs must avoid filename collisions.
- When needed, numeric disambiguation is applied.

## ZIP and Manifest Contract

When the result is a ZIP:

- It contains the transformed files.
- It contains `manifest.json`.
- The manifest includes:
  - processed file entries
  - error entries when failures occur during processing
  - summary totals

### Manifest summary fields

- `totalFiles`
- `processedFiles`
- `failedFiles`
- `totalOriginalBytes`
- `totalOptimizedBytes`

### Manifest file fields

- `source`
- `output`
- `originalBytes`
- `optimizedBytes`
- `compressionRatio`
- `originalFormat`
- `outputFormat`
- `originalDimensions`
- `outputDimensions`

## Limits and Validation

### Stable limits

- Maximum **100 files** per request
- Maximum **50 MB** total upload size per request
- Maximum **50 megapixels** per image
- Maximum **120 seconds cumulative processing time per request**
- `max_width` and `max_height` accept values in `1..10000`

### Stable validation behavior

- Unsupported input formats are rejected or skipped depending on where they are detected.
- Corrupt image files produce a specific processing error.
- Oversized images produce a specific processing error.
- Invalid quality and dimension inputs produce specific validation errors.

## Error Contract

The product should prefer **specific** errors over generic ones.

Known stable error families at `1.0.0` include:

- `UNSUPPORTED_INPUT_FORMAT`
- `UNSUPPORTED_OUTPUT_FORMAT`
- `INVALID_IMAGE`
- `INVALID_DIMENSIONS`
- `INVALID_QUALITY`
- `FILE_COUNT_LIMIT`
- `TOTAL_SIZE_LIMIT`
- `IMAGE_TOO_LARGE`
- `PROCESSING_TIMEOUT`
- `INVALID_PATHS_FORMAT`
- `AVIF_UNAVAILABLE`
- `INVALID_NAMING_CONFIG`

## Operational Baseline

At `1.0.0`, this version has already been validated with:

- runtime AVIF validation in the Docker target environment
- smoke HTTP validation for core API flows
- minimal browser smoke validation for single-file and batch happy paths
- real releases executed through `scripts/release.sh`
- required status checks active for frontend and backend CI

## Non-goals / Not Promised by 1.0.0

These are **not** part of the stable promise unless a later version says otherwise:

- async job processing
- progress bars backed by background workers
- authentication
- advanced image editing
- support for arbitrary legacy formats beyond the declared set
- broad browser E2E coverage beyond the current smoke baseline

## When to Update This Document

Update this document when a change affects:

- user-visible workflow behavior
- supported formats
- limits
- ZIP / manifest structure
- naming rules
- error contract
- release/runtime assumptions that users or maintainers depend on

## Related References

- `README.md` — public overview and roadmap
- `docs/setup.md` — setup, runtime validation, troubleshooting
- `docs/environment.md` — runtime/env reference
- `docs/release-process.md` — release lane
- `apps/api/tests/test_smoke.py` — live API smoke baseline
- `apps/web/e2e/smoke.spec.ts` — browser smoke baseline

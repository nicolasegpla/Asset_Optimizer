# Asset Optimizer 1.1.0 Contract

This document is the **frozen product contract** for Asset Optimizer `1.1.0`.

It extends the `1.0.0` contract with GLB (3D model) optimization support while keeping all previous image processing behavior unchanged.

## What Changed from 1.0.0

| Area | 1.0.0 | 1.1.0 |
|------|-------|-------|
| Input formats | `jpg`, `jpeg`, `png`, `webp` | `jpg`, `jpeg`, `png`, `webp`, **`glb`** |
| Output formats | `jpg`, `png`, `webp`, `avif` | `jpg`, `png`, `webp`, `avif`, **`glb`** |
| GLB optimization | N/A | Draco compression, deduplication, pruning, quantization |
| File type mixing | N/A | **Prevented** (images + GLB rejected) |
| GLB per-file limit | N/A | **100 MB** |
| GLB batch total limit | N/A | **500 MB** |

## Current Contract

| Area | 1.1.0 decision |
|------|----------------|
| Input formats | `jpg`, `jpeg`, `png`, `webp`, `glb` |
| Output formats | `jpg`, `png`, `webp`, `avif`, `glb` |
| Processing model | Synchronous |
| Single file result | Direct file download |
| Multi-file / folder result | ZIP download |
| Folder handling | Preserve relative paths when available |
| Batch metadata | `manifest.json` included in ZIP |
| Partial success | Supported |
| AVIF availability | Runtime-dependent, exposed by `/api/v1/capabilities` |
| GLB optimization | Runtime-dependent, exposed by `/health` |
| Image limits | 100 files, 50 MB total, 50 MP per image |
| GLB limits | 100 files, **500 MB total**, 100 MB per file |
| Mixed file types | **Rejected** — images and GLB cannot be mixed |

## Product Promise

Asset Optimizer is not just a format converter.

At `1.1.0`, the stable promise is:

> Prepare web-ready image and 3D assets with reliable conversion, compression, resize, naming, and batch packaging behavior.

## Stable User Flows

### 1. Single file optimization (images)

- User uploads one supported image.
- User chooses output format, quality, and optional dimensions.
- App returns a direct file download.
- Result UI shows original vs optimized size and, when possible, before/after comparison.

### 2. Single file optimization (GLB)

- User uploads one `.glb` file.
- App applies Draco compression, deduplication, pruning, and quantization.
- App returns an optimized `.glb` download.
- Result UI shows file size reduction.

### 3. Multi-file batch optimization

- User uploads two or more supported files (all images OR all GLB).
- App returns a ZIP file.
- ZIP includes transformed files plus `manifest.json`.
- Result UI shows batch summary, processed files, and manifest actions.

### 4. Folder optimization

- User selects a folder from the browser.
- Supported files inside the folder are processed.
- Relative structure is preserved in the ZIP when the browser/runtime provides path information.
- ZIP naming is separate from internal output naming.

### 5. Partial success

- Invalid or failed files do not block valid files from returning.
- Pre-upload unsupported files can be skipped before upload.
- Backend processing failures appear in the manifest `errors` array.
- Result summary distinguishes processed output from failures/skips.

## Formats and GLB Rules

### Supported input

- `JPG / JPEG`
- `PNG`
- `WEBP`
- **`GLB` (glTF Binary)**

### Supported output

- `JPG / JPEG`
- `PNG`
- `WEBP`
- `AVIF`
- **`GLB` (optimized)**

### GLB contract

- GLB optimization is **runtime-dependent**, not assumed blindly.
- The backend validates `gltf-transform` CLI availability at startup.
- `/health` exposes whether GLB optimization is available via `gltf_transform_available`.
- The frontend shows a clear error when GLB runtime is unavailable.
- If GLB optimizer is unavailable in a given runtime, the backend remains the final authority.

### GLB optimization settings

At `1.1.0`, the following optimizations are applied by default:

- **Draco compression** — geometry compression
- **Deduplication** — remove redundant accessors and meshes
- **Pruning** — remove unused nodes, meshes, materials
- **Quantization** — reduce precision where safe

### Mixed file types rule

- **Images and GLB files cannot be mixed in the same upload.**
- The frontend prevents mixed selection before upload.
- The backend rejects mixed requests with `MIXED_FILE_TYPES` error.

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

### Image limits

- Maximum **100 files** per request
- Maximum **50 MB** total upload size per request
- Maximum **50 megapixels** per image
- Maximum **120 seconds cumulative processing time per request**
- `max_width` and `max_height` accept values in `1..10000`

### GLB limits

- Maximum **100 files** per request
- Maximum **500 MB** total upload size per GLB batch
- Maximum **100 MB** per individual GLB file
- Maximum **120 seconds cumulative processing time per request**

### Validation behavior

- Unsupported input formats are rejected or skipped depending on where they are detected.
- Corrupt image files produce a specific processing error.
- Oversized images produce a specific processing error.
- Oversized GLB files produce a `GLB_TOO_LARGE` error.
- Mixed file types (images + GLB) produce a `MIXED_FILE_TYPES` error.
- Invalid quality and dimension inputs produce specific validation errors.

## Error Contract

The product should prefer **specific** errors over generic ones.

Known stable error families at `1.1.0` include:

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
- **`INVALID_GLB`**
- **`GLB_TOO_LARGE`**
- **`GLB_OPTIMIZATION_FAILED`**
- **`GLB_RUNTIME_UNAVAILABLE`**
- **`MIXED_FILE_TYPES`**

## Operational Baseline

At `1.1.0`, this version has been validated with:

- runtime AVIF validation in the Docker target environment
- runtime GLB validation (`gltf-transform` CLI) in the Docker target environment
- smoke HTTP validation for core API flows
- minimal browser smoke validation for single-file and batch happy paths
- real releases executed through `scripts/release.sh`
- required status checks active for frontend and backend CI

## Non-goals / Not Promised by 1.1.0

These are **not** part of the stable promise unless a later version says otherwise:

- async job processing
- progress bars backed by background workers
- authentication
- advanced image editing
- 3D model preview / viewer in the browser
- mesh simplification / decimation
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
- GLB optimization behavior
- release/runtime assumptions that users or maintainers depend on

## Related References

- `README.md` — public overview and roadmap
- `docs/version-1-0-0.md` — previous version contract (images only)
- `docs/setup.md` — setup, runtime validation, troubleshooting
- `docs/environment.md` — runtime/env reference
- `docs/release-process.md` — release lane
- `apps/api/tests/test_smoke.py` — live API smoke baseline
- `apps/web/e2e/smoke.spec.ts` — browser smoke baseline

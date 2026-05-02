# Monorepo Notes

## Services

- `apps/web`: React + TypeScript client
- `apps/api`: FastAPI backend

## Local Startup

When Docker is available, both services should be started with one command:

```bash
docker compose up --build
```

## Current Status

- Docker Compose wiring is in place for local development
- Frontend supports single image and folder/batch uploads
- Frontend exposes product presets, visible upload limits, junk/system file filtering, and a single-image before/after comparison
- Backend exposes health, formats, limits, and the synchronous transform pipeline with ZIP output for multi-file/folder uploads

## API Contract

### `POST /api/v1/transform`

**Request**: `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `files` | file[] | One or more image files (JPG, JPEG, PNG, WEBP) |
| `output_format` | string | `jpg`, `png`, `webp`, or `avif` |
| `quality` | int | 1–100 |
| `max_width` | int? | Optional max width in pixels |
| `max_height` | int? | Optional max height in pixels |
| `paths` | string? | Optional JSON array of source-relative paths, one per file in the same order as `files`. Used to preserve folder structure in batch ZIPs. Canonical shape: `["subdir/file.jpg", "other/img.png"]`. Legacy shape: `{"filename.jpg": "subdir/filename.jpg"}` (backward compat). Omit to fall back to flat ZIP using `webkitRelativePath` or filename. |

**Limits**:
- Max 100 files per request
- Max 50 MB total upload size
- Max 50 megapixels per image
- Max 120 seconds processing time
- `max_width` / `max_height`: 1–10000 (inclusive)

**Single file response** (`200`):
- `Content-Type: image/{format}`
- `Content-Disposition: attachment; filename="{name}.{ext}"`
- `X-Asset-Original-Bytes: <int>`
- `X-Asset-Optimized-Bytes: <int>`
- `X-Asset-Compression-Ratio: <float>`
- Body: binary image data

**Batch response** (`200`):
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="optimized-assets.zip"`
- `X-Asset-Processed-Count: <int>`
- `X-Asset-Original-Bytes: <int>`
- `X-Asset-Optimized-Bytes: <int>`
- `X-Asset-Error-Count: <int>` — present when any file in the batch failed (partial or all-fail)
- Body: binary ZIP data preserving relative folder paths from `paths` field (or `webkitRelativePath` if omitted)
- The ZIP always contains `manifest.json` at root when ≥2 files are submitted successfully

**Partial success** (`200`): When some files succeed and others fail, the ZIP contains all successfully processed files plus `manifest.json` with per-file success/error records. The `X-Asset-Error-Count` header reports the number of failures.

**All-fail** (`422`): When every file in the batch fails validation or transformation, the API returns JSON with a top-level `error.details.errors` array listing each failed file and its error code/message. No ZIP is generated.

**Single file response** (`200`):
- `Content-Type: image/{format}`
- `Content-Disposition: attachment; filename="{name}.{ext}"`
- `X-Asset-Original-Bytes: <int>`
- `X-Asset-Optimized-Bytes: <int>`
- `X-Asset-Compression-Ratio: <float>`
- Body: binary image data (no ZIP, no manifest)

### Batch ZIP manifest.json

Every batch ZIP (≥2 successfully processed files) includes a `manifest.json` at the archive root. This file provides per-file processing metadata for programmatic consumption of the ZIP contents.

**Schema:**
```json
{
  "files": [
    {
      "source": "original-filename.png",
      "output": "optimized-filename.webp",
      "originalBytes": 245000,
      "optimizedBytes": 48000,
      "compressionRatio": 0.8039,
      "originalFormat": "png",
      "outputFormat": "webp",
      "originalDimensions": { "width": 1200, "height": 800 },
      "outputDimensions": { "width": 600, "height": 400 }
    }
  ],
  "errors": [
    {
      "source": "corrupt-file.png",
      "code": "INVALID_IMAGE",
      "message": "File 'corrupt-file.png' is corrupt or not a valid image."
    }
  ],
  "summary": {
    "totalFiles": 3,
    "processedFiles": 2,
    "failedFiles": 1,
    "totalOriginalBytes": 500000,
    "totalOptimizedBytes": 96000
  }
}
```

**Notes:**
- `output` values reflect collision-resolved filenames (e.g., `image-2.webp`) matching actual ZIP entries
- `compressionRatio` is a float (0–1), e.g., 0.80 means 80% compression (20% reduction)
- The manifest is UTF-8 encoded and pretty-printed (2-space indent) for readability
- Single-file downloads do not include `manifest.json`

**Error response** (`422`):
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

**Error Codes**:
- `UNSUPPORTED_INPUT_FORMAT` — file has unsupported input format
- `UNSUPPORTED_OUTPUT_FORMAT` — requested output format not supported
- `INVALID_IMAGE` — file is corrupt or not a valid image
- `INVALID_DIMENSIONS` — max_width/max_height must be between 1 and 10000
- `INVALID_QUALITY` — quality must be between 1 and 100
- `FILE_COUNT_LIMIT` — too many files (max 100)
- `TOTAL_SIZE_LIMIT` — total upload size exceeds 50 MB
- `IMAGE_TOO_LARGE` — single image exceeds 50 megapixels
- `PROCESSING_TIMEOUT` — processing exceeded 120 seconds
- `INVALID_PATHS_FORMAT` — `paths` field is malformed, has mismatched file count, absolute paths, drive prefixes, or `..` traversal

### `GET /api/v1/formats`

Returns supported input/output formats:

```json
{
  "input_formats": ["jpg", "jpeg", "png", "webp"],
  "output_formats": ["jpg", "png", "webp", "avif"]
}
```

### `GET /api/v1/limits`

Returns backend-enforced limits so the frontend can show them before processing.

```json
{
  "max_files": 100,
  "max_total_bytes": 52428800,
  "max_pixels": 52428800
}
```

### `GET /health`

Returns API health status.

## Frontend UX Notes

- Presets currently available:
  - `E-commerce Product`
  - `Hero / Banner`
  - `Thumbnail`
  - `Open Graph`
- Folder uploads filter obvious junk/system files before format validation:
  - `.DS_Store`
  - `Thumbs.db`
  - `desktop.ini`
  - `._*`
  - files inside `__MACOSX`, `.git`, `.vscode`
- If the limits endpoint is unavailable, the frontend falls back silently to the known defaults:
  - `100 files`
  - `50 MB total upload size`
  - `50 megapixels per image`
- The app version shown in the UI comes from `apps/web/package.json`.

## Architecture Notes

- Image transformation runs synchronously in-memory (v1)
- Batch ZIP structure is driven by the optional `paths` multipart field (canonical: ordered array matching file order). Fallback: `webkitRelativePath` or filename.
- Filename collisions in the archive are resolved by appending `-1`, `-2` suffixes (handled in `archive.py`)
- RGBA → RGB conversion for JPG output uses white background compositing
- AVIF support via `pillow-avif-plugin` (requires `libaom-dev` in Docker)
- Processing pipeline is organized for future async job migration

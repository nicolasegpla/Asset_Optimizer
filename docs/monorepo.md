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

- Docker Compose wiring is in place
- Frontend renders the product shell and checks API health
- Backend exposes health, formats, and a first batch contract endpoint
- Real image transformation pipeline is the next implementation step

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
- Body: binary ZIP data preserving relative folder paths

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

### `GET /api/v1/formats`

Returns supported input/output formats:

```json
{
  "input_formats": ["jpg", "jpeg", "png", "webp"],
  "output_formats": ["jpg", "png", "webp", "avif"]
}
```

### `GET /health`

Returns API health status.

## Architecture Notes

- Image transformation runs synchronously in-memory (v1)
- ZIP creation preserves `webkitRelativePath` folder structure
- Filename collisions resolved with `-1`, `-2` numeric suffixes
- RGBA → RGB conversion for JPG output uses white background compositing
- AVIF support via `pillow-avif-plugin` (requires `libaom-dev` in Docker)
- Processing pipeline is organized for future async job migration

# Asset Optimizer

Asset Optimizer is a web product focused on preparing images for websites, e-commerce, and digital products.

It is not just a generic format converter. The goal is to help users convert, compress, resize, and package assets so they are ready for publishing with better performance, compatibility, and lower file size.

## Product Positioning

> Convert, compress, and adapt images for web and e-commerce in seconds.

## Target Users

- People building websites
- E-commerce teams managing product images
- Creators preparing assets for digital products
- Developers and designers optimizing images for the web

## Current Version

- Frontend: `0.5.0`
- Versioning policy: Semantic Versioning in `0.x` until runtime, contract, and UX are stable enough for `1.0.0`

## Monorepo Structure

```txt
asset-optimizer/
  apps/
    web/   # React + TypeScript frontend
    api/   # FastAPI backend
  docs/
  docker-compose.yml
  README.md
  CLAUDE.md
```

## Tech Stack

### Frontend
- React 19
- TypeScript
- Vite
- Vitest + React Testing Library + happy-dom

### Backend
- Python
- FastAPI
- Pillow / AVIF plugin support

### Local Environment
- Docker Compose
- Bun for local frontend dependency workflow

## Supported Formats

### Input
- JPG / JPEG
- PNG
- WEBP

### Output
- JPG / JPEG
- PNG
- WEBP
- AVIF

## Core Features

- Upload one or multiple image files
- Select a full folder from the browser
- Convert between supported formats
- Adjust output quality / compression
- Resize by dimensions
- See original vs optimized size
- Download a single transformed file
- Download batch transformations as a ZIP file
- Single-image before/after comparison
- Batch manifest metadata inside ZIPs
- Partial success in batch processing

## Batch Processing Rules

- Single file → direct download
- Multiple files or folder → ZIP download
- Folder uploads preserve relative paths when available
- Batch ZIPs include `manifest.json` with per-file outputs, errors, and summary totals
- Partial success is supported: valid files still return even if some files fail

## Local Development

### Start the app

```bash
docker compose up -d
```

The default local ports are:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`

### Frontend dependency install

If you are working directly inside `apps/web` on the host:

```bash
cd apps/web
bun install
```

If the running web container needs updated dependencies after package changes:

```bash
docker compose exec web npm install
```

## API Overview

### `POST /api/v1/transform`

`multipart/form-data`

Fields:

- `files` → one or more image files
- `output_format` → `jpg`, `png`, `webp`, `avif`
- `quality` → integer `1..100`
- `max_width` → optional
- `max_height` → optional
- `paths` → optional ordered JSON array for folder structure preservation

### `GET /api/v1/formats`

Returns supported input and output formats.

### `GET /api/v1/limits`

Returns backend-enforced limits for frontend display.

### `GET /health`

Returns API health status.

## Processing Limits

- Max 100 files per request
- Max 50 MB total upload size
- Max 50 megapixels per image
- Max 120 seconds processing time
- `max_width` / `max_height`: `1..10000`

## Frontend UX Notes

- Presets currently available:
  - E-commerce Product
  - Hero / Banner
  - Thumbnail
  - Open Graph
- Folder uploads filter junk/system files before format validation:
  - `.DS_Store`
  - `Thumbs.db`
  - `desktop.ini`
  - `._*`
  - files inside `__MACOSX`, `.git`, `.vscode`
- If `/api/v1/limits` is unavailable, the frontend falls back silently to defaults.

## Testing

### Frontend

```bash
cd apps/web
bun test
bun run test:watch
```

### Backend

Run the Python test suite from the API app environment as appropriate for your setup.

## Architecture Notes

- Processing is synchronous in the current product line
- Batch ZIP structure is driven by the optional `paths` field
- Filename collisions in ZIPs are resolved with numeric suffixes
- JPG output composites transparency onto white background
- AVIF support depends on runtime/container support and should be validated in the deployment environment

## Versioning Policy

This project follows Semantic Versioning (`MAJOR.MINOR.PATCH`), but remains in `0.x` while the product contract and runtime behavior are still evolving.

### Practical meaning

- `0.1.0` → first functional MVP
- `0.2.0` → product/UX foundation
- `0.3.0` → pragmatic batch UX improvements
- `0.4.0` → frontend quality sprint
- `0.5.0` → runtime and operational hardening
- `1.0.0` → first stable public-ready baseline

## Roadmap

### Completed

#### v0.1.0
- MVP base functional
- Single + batch transform
- ZIP output
- Single-image comparison
- Friendly errors
- Monorepo + Docker dev

#### v0.2.0
- Presets
- Visible limits
- Junk/system file filtering
- Initial `App.tsx` refactor

#### v0.3.0
- `manifest.json` inside ZIP
- Partial success for batch/folder uploads
- Improved batch summary
- Large-batch warnings

#### v0.4.0
- Vitest + happy-dom test harness
- First wave of frontend tests
- Contract/constants extraction
- Batch UX polish
- Frontend aligned to `0.4.0`

#### v0.5.0
- Runtime AVIF capability detection and honest fallback behavior
- `/api/v1/capabilities` endpoint
- Enriched `/health` and Docker healthchecks
- Structured runtime logging with request ID and timing
- Frontend AVIF availability UX aligned to real backend capabilities
- Operational setup and troubleshooting docs

### Next

#### v0.6.0 — Stronger product UX

4. Better batch UX
- Better sorting/filtering of results
- Group by success/error/skipped
- Clearer actions around manifest information

5. Naming/output controls
- Rename rules
- Batch naming strategy
- Better control over final ZIP / output names

6. Format guidance
- When to use WEBP
- When to use AVIF
- When JPG or PNG is a better choice
- Smarter recommendations by use case

#### v0.7.0 — Release quality

7. CI basics
- Backend tests
- Frontend tests
- Minimum automated checks

8. Deploy/release flow
- Clear release strategy
- Version bump policy enforcement
- Optional stronger tag/release visibility

9. Runtime/onboarding docs
- Local setup
- Troubleshooting
- Dependency/environment guidance

### v1.0.0

Target only when:

- Frontend and backend are both reliable
- AVIF is validated in runtime
- Development environment is stable
- CI exists
- Contract is mature
- Batch UX is strong
- Docs are coherent

## Notes

- SDD planning artifacts are tracked in Engram and ignored from git (`sdd/` is ignored).
- Project conventions and deeper planning context also live in `CLAUDE.md` and `docs/monorepo.md`.

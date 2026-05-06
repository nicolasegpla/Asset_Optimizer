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

- Asset Optimizer: **0.8.0** (web + API aligned)
- Versioning policy: Semantic Versioning in `0.x` until runtime, contract, and UX are stable enough for `1.0.0`
- See [Release Process](./docs/release-process.md) to cut a release

## Quickstart

Get a running instance in under 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/asset-optimizer.git
cd asset-optimizer

# 2. Start the app
docker compose -f docker-compose.yml up -d

# 3. Verify the API is up
curl http://localhost:8000/health

# 4. Open the web UI
# → http://localhost:5173
```

If you want to understand the environment variables and what they do, see [Environment Reference](./docs/environment.md). For host-side setup, dependency details, and troubleshooting, see [Setup & Operations](./docs/setup.md).

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

For full setup details (host-side frontend/backend, Docker commands, troubleshooting), see [Setup & Operations](./docs/setup.md).

Key references:

| Need | Go to |
|------|-------|
| Start both services | `docker compose up -d` |
| Frontend on host (`bun`) | [Setup: Frontend](./docs/setup.md#frontend-react--vite) |
| Backend on host (Python) | [Setup: Backend](./docs/setup.md#backend-fastapi) |
| Port conflicts, stale volumes, rebuilds | [Setup: Docker Troubleshooting](./docs/setup.md#docker-troubleshooting) |
| Backend testing (`pytest`) | [Setup: Backend Testing](./docs/setup.md#backend-testing) |
| What env vars mean | [Environment Reference](./docs/environment.md) |

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
- Batch result UX now includes:
  - All / Success / Failed grouped result views
  - Richer sorting across name, savings, sizes, format, and dimensions
  - Separate skipped-file banner for pre-upload exclusions
  - Manifest download and copy-summary actions
- Naming controls now include:
  - Single-file prefix/suffix naming without forced renumbering
  - Batch/folder basename replacement via sequential `output_stem-N`
  - Custom ZIP naming handled separately from internal output paths
- Format guidance now includes:
  - Collapsible format guide with transparency and compatibility hints
  - Preset rationale shown next to optimization presets
  - Clearer AVIF availability and caution messaging
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
- `0.6.0` → stronger batch result UX
- `0.7.0` → output naming controls and format guidance
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

#### v0.6.0
- Batch result tabs for All / Success / Failed outcomes
- Richer batch sorting across name, savings, original size, optimized size, format, and dimensions
- Inline failed-row errors with clearer visual distinction
- Separate skipped-file banner for pre-upload exclusions
- Manifest actions for JSON download and copyable batch summary

#### v0.7.0
- Single-file naming keeps original basename with optional prefix/suffix
- Batch and folder naming replace basenames entirely with sequential `output_stem-N`
- ZIP name customization is separated from internal output naming
- Static format guidance catalog explains transparency, compatibility, and best-fit use cases
- Collapsible `FormatGuide` UI and preset rationale improve format selection confidence
- AVIF guidance and availability messaging are clearer in the transformation settings panel

#### v0.8.0
- Quickstart guide in README for first-run local startup
- `docs/environment.md` canonical runtime and environment reference
- Expanded `.env.example` with inline operational comments
- `docs/setup.md` Docker troubleshooting and backend testing sections
- GitHub Actions CI with parallel frontend and backend test jobs
- Manual release flow with `scripts/release.sh`, annotated tags, and release docs

### Next

### v1.0.0

Target only when:

- Frontend and backend are both reliable
- AVIF is validated in runtime
- Development environment is stable
- CI exists
- Contract is mature
- Batch UX is strong
- Docs are coherent

#### Mini roadmap toward v1.0.0

1. AVIF runtime validation
   - Validate AVIF support in the real server/runtime environment
   - Confirm successful JPG, PNG, and WEBP to AVIF transformations under the target deployment setup
   - Verify the fallback UX remains honest when AVIF is unavailable at runtime

2. End-to-end smoke validation
   - Run smoke tests for single-file, multi-file, and folder upload flows
   - Verify naming controls, ZIP output structure, and `manifest.json` behavior
   - Confirm partial-success batches behave consistently outside local development

3. Release path proof
   - Execute a real release using `scripts/release.sh`
   - Verify synchronized version bumps for web and API, annotated tags, and push behavior
   - Confirm the documented rollback path is accurate in practice

4. Operational enforcement
   - Keep GitHub Actions CI green on `main`
   - Enable required status checks for `web-tests` and `api-tests`
   - Treat CI as a merge gate, not only as passive feedback

5. Final contract review
   - Review the public product contract for naming, batch ZIP, manifest, limits, and error behavior
   - Confirm docs remain aligned with actual runtime and release behavior
   - Decide whether the project is stable enough to promote from `0.8.x` to `1.0.0`

## Notes

- SDD planning artifacts are tracked in Engram and ignored from git (`sdd/` is ignored).
- Project conventions and deeper planning context also live in `CLAUDE.md` and `docs/monorepo.md`.

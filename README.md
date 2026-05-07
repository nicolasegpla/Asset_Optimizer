<p align="center">
  <img src="./apps/web/public/logo-app.svg" alt="Asset Optimizer logo" width="120" />
</p>

<h1 align="center">Asset Optimizer</h1>

<p align="center">
  <strong>Convert, compress, resize, and package web-ready image assets.</strong>
</p>

<p align="center">
  Built for websites, e-commerce, and digital products that need lighter assets without losing workflow clarity.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-2f855a?style=flat-square" />
  <img alt="Frontend" src="https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-2563eb?style=flat-square" />
  <img alt="Backend" src="https://img.shields.io/badge/backend-FastAPI-059669?style=flat-square" />
  <img alt="Deploy" src="https://img.shields.io/badge/deploy-Railway-7c3aed?style=flat-square" />
</p>

---

## ✨ Why this project exists

Asset Optimizer is focused on one job: preparing images so they are actually ready to publish.

It is not just a generic format converter. The product goal is to help users convert, compress, resize, and package assets so they ship with better performance, better compatibility, and lower file size.

## 🎯 Who it is for

- People building websites
- E-commerce teams managing product images
- Creators preparing assets for digital products
- Developers and designers optimizing images for the web

## 🚀 Current baseline

| Topic | Status |
|------|--------|
| Stable version | **1.0.0** |
| Product contract | Frozen in [`docs/version-1-0-0.md`](./docs/version-1-0-0.md) |
| Release lane | [`docs/release-process.md`](./docs/release-process.md) |
| Runtime / env reference | [`docs/environment.md`](./docs/environment.md) |
| Setup / operations | [`docs/setup.md`](./docs/setup.md) |

## ⚡ Quickstart

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

If you want to understand the environment variables and what they do, see [Environment Reference](./docs/environment.md). For host-side setup, dependency details, troubleshooting, and Railway notes, see [Setup & Operations](./docs/setup.md).

## 🧭 At a glance

### Core flows

- Upload one file and get a direct optimized download
- Upload multiple files or a folder and get a ZIP package
- Keep batch metadata with `manifest.json`
- Use AVIF only when the runtime actually supports it
- Preserve folder paths when the browser provides them

### Supported formats

| Input | Output |
|------|--------|
| JPG / JPEG | JPG / JPEG |
| PNG | PNG |
| WEBP | WEBP |
| — | AVIF |

### Key product rules

- **Single file** → direct file download
- **Multiple files / folder** → ZIP download
- **Batch ZIPs** include `manifest.json`
- **Partial success** is supported, valid files still return when others fail

## 🏗️ Monorepo structure

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

## 🧰 Tech stack

| Layer | Tools |
|------|-------|
| Frontend | React 19, TypeScript, Vite |
| Backend | Python, FastAPI, Pillow, pillow-avif-plugin |
| Testing | Vitest, React Testing Library, pytest, Playwright smoke |
| Local infra | Docker Compose, Bun |
| Deploy | Railway |

## ✅ Core features

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

## 📦 Batch processing rules

- Single file → direct download
- Multiple files or folder → ZIP download
- Folder uploads preserve relative paths when available
- Batch ZIPs include `manifest.json` with per-file outputs, errors, and summary totals
- Partial success is supported: valid files still return even if some files fail

## 🛠️ Local development

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

## 🔌 API overview

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

## 📏 Processing limits

- Max 100 files per request
- Max 50 MB total upload size
- Max 50 megapixels per image
- Max 120 seconds cumulative processing time per request
- `max_width` / `max_height`: `1..10000`

## 🖥️ Frontend UX notes

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

## 🧪 Testing

### Frontend

```bash
cd apps/web
bun test
bun run test:watch
```

### Backend

Run the Python test suite from the API app environment as appropriate for your setup.

## 🧠 Architecture notes

- Processing is synchronous in the current product line
- Batch ZIP structure is driven by the optional `paths` field
- Filename collisions in ZIPs are resolved with numeric suffixes
- JPG output composites transparency onto white background
- AVIF support depends on runtime/container support and should be validated in the deployment environment

## 🔖 Versioning policy

This project follows Semantic Versioning (`MAJOR.MINOR.PATCH`). `1.0.0` marks the first stable public baseline for the current product contract.

### Practical meaning

- `0.1.0` → first functional MVP
- `0.2.0` → product/UX foundation
- `0.3.0` → pragmatic batch UX improvements
- `0.4.0` → frontend quality sprint
- `0.5.0` → runtime and operational hardening
- `0.6.0` → stronger batch result UX
- `0.7.0` → output naming controls and format guidance
- `0.9.0` → final stabilization release before stable baseline
- `1.0.0` → first stable public-ready baseline

## 🗺️ Roadmap

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

#### v0.9.0
- Final contract stabilization pass before stable release
- AVIF runtime validation confirmed in Docker target runtime
- API smoke validation plus browser smoke coverage added
- Required status checks activated on `main`
- Public contract review closed with docs and UX drift corrected

#### v1.0.0
- Stable public baseline declared
- Release flow proven with real tags and pushes
- Core contract frozen in [`docs/version-1-0-0.md`](./docs/version-1-0-0.md)

### Next

### v1.0.0

`v1.0.0` has already been reached.

Use [`docs/version-1-0-0.md`](./docs/version-1-0-0.md) as the source of truth for the stable contract before planning future changes.

## 📝 Notes

- SDD planning artifacts are tracked in Engram and ignored from git (`sdd/` is ignored).
- Project conventions and deeper planning context also live in `CLAUDE.md` and `docs/monorepo.md`.

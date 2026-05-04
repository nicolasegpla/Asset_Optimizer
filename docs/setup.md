# Asset Optimizer — Setup & Operations

## Project Structure

```
asset-optimizer/
├── apps/
│   ├── api/       # FastAPI backend (Python)
│   └── web/       # React frontend (TypeScript/Vite)
├── docs/
└── docker-compose.yml
```

## Local Development

### Frontend (React + Vite)

Requires Node.js and Bun (or npm/pnpm).

```bash
cd apps/web
bun install
bun run dev
# → http://localhost:5173
```

The frontend expects the API at `VITE_API_BASE_URL` (default: `http://localhost:8000`).

### Backend (FastAPI)

Option A — Direct (Python):
```bash
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
```

Option B — Docker:
```bash
docker compose up api
# → http://localhost:8000
```

## Docker Compose (Full Stack)

```bash
docker compose up
# → API: http://localhost:8000
# → Web: http://localhost:5173
```

The `api` service includes a healthcheck that polls `/health` every 30s.

## Runtime Capabilities

### Checking Available Formats

```bash
curl http://localhost:8000/api/v1/capabilities
```

Returns:
```json
{
  "output_formats": ["jpg", "png", "webp", "avif"],
  "avif_available": true
}
```

`avif` appears in `output_formats` only when AVIF encoding is detected as working at startup.

### Health Endpoint

```bash
curl http://localhost:8000/health
```

Returns dependency and AVIF status:
```json
{
  "status": "online",
  "service": "asset-optimizer-api",
  "avif_available": true,
  "dependencies": {
    "pillow": { "version": "11.x.x", "status": "ok" },
    "avif_encoder": { "available": true, "status": "ok" }
  }
}
```

## AVIF Support — Troubleshooting

AVIF encoding requires the `pillow-avif-plugin` package and `libaom-dev` system library. See [Environment Reference](./environment.md#avif-runtime-detection) for details on how AVIF availability is detected at runtime.

### Symptoms

- `/api/v1/capabilities` returns `avif_available: false`
- `/health` shows `avif_encoder.status: "unavailable"`
- Startup logs: `Startup: AVIF=False, Pillow=...`

### Fix — Local (Python)

```bash
pip install pillow-avif-plugin
# Restart the API server
```

### Fix — Docker

The Dockerfile installs `libaom-dev`. If AVIF is still unavailable, rebuild:

```bash
docker compose build --no-cache api
docker compose up api
```

### Verify Fix

```bash
curl http://localhost:8000/api/v1/capabilities | grep avif_available
```

Should return `"avif_available": true`.

## Docker Troubleshooting

### Frontend `npm install` fails on Alpine with `EBADPLATFORM`

If the `web` image fails during `npm install` with an error similar to:

```text
Unsupported platform for @rollup/rollup-linux-x64-gnu
current: libc musl
wanted: libc glibc
```

the frontend dependency tree is forcing a glibc-only Rollup binary while `node:alpine` runs on musl.

#### Fix

- Do **not** declare `@rollup/rollup-linux-x64-gnu` as a direct dependency in `apps/web/package.json`
- Keep `rollup` as the dependency and let the package manager resolve the correct optional binary for the container platform
- Rebuild the web image after updating the lockfile

This repository is expected to work with `apps/web/Dockerfile` based on Alpine, so platform-specific Rollup binaries must stay out of direct dependencies.

### Port conflicts

If port `5173` (web) or `8000` (api) are already in use:

```bash
# Find what's using the port
lsof -i :5173
lsof -i :8000

# Kill the process or stop the service
kill <PID>
docker compose down
```

Then restart with `docker compose up`.

### Stale volumes

If the database or data volume is in a bad state, remove it before restarting:

```bash
docker compose down -v
docker compose up -d
```

### Image rebuild

If you suspect a corrupted or outdated image:

```bash
docker compose build --no-cache
docker compose up -d
```

## Backend Testing

### Setup

Create a Python virtual environment and install test dependencies:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
```

### Run all tests

```bash
pytest
```

### Run a single test file

```bash
pytest tests/test_api.py
```

### Run tests matching a pattern

```bash
pytest -k "transform"
```

Test files are located in `apps/api/tests/`. Run pytest from the `apps/api/` directory (or pass the path explicitly).

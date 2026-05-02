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

AVIF encoding requires the `pillow-avif-plugin` package and `libaom-dev` system library.

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
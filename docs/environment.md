---
title: Environment Reference
description: Canonical runtime and environment variable reference for Asset Optimizer.
---

# Environment Reference

This document is the authoritative reference for all runtime environment variables and port configuration in Asset Optimizer. For a quick setup walkthrough, see [Setup & Operations](./setup.md).

## Environment Variables

| Name | Service | Type | Default | Example | Effect |
|------|---------|------|---------|---------|--------|
| `VITE_API_BASE_URL` | web | URL string | `http://localhost:8000` | `http://localhost:8000` | Sets the API endpoint the frontend calls. Read at build time by Vite. |
| `CORS_ORIGINS` | api | comma-separated URLs | `http://localhost:5173,http://127.0.0.1:5173` | `https://myapp.vercel.app` | Configures FastAPI CORS middleware. Each origin must be a full URL. |

## Ports

| Service | Default Port | URL |
|---------|-------------|-----|
| Web (Vite dev server) | `5173` | `http://localhost:5173` |
| API (FastAPI) | `8000` | `http://localhost:8000` |

## CORS Configuration

`CORS_ORIGINS` accepts a comma-separated list of full URLs with no spaces:

```
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://myapp.vercel.app
```

The FastAPI CORS middleware will block any browser request originating from an origin not in this list. This is relevant when running the frontend and API on different ports in local development, or when deploying the web app to a hosted domain.

## AVIF Runtime Detection

AVIF encoding availability is detected at API startup via `pillow-avif-plugin`. It is NOT configured via an environment variable — the presence of the plugin and the `libaom-dev` system library determines the runtime capability.

### Checking AVIF availability

```bash
curl http://localhost:8000/api/v1/capabilities
```

Response:
```json
{
  "output_formats": ["jpg", "png", "webp", "avif"],
  "avif_available": true
}
```

`avif_available: true` means AVIF encoding is working. If AVIF is unavailable, `avif_available` is `false` and `avif` does not appear in `output_formats`. See [Setup & Operations](./setup.md#avif-support--troubleshooting) for fix instructions.

### Validated Runtime Baseline

The current project baseline has already been validated in the Docker runtime defined by this repo:

- container path: `docker compose` -> `api`
- base image: `python:3.12-slim`
- AVIF positive path confirmed for `JPG -> AVIF`, `PNG -> AVIF`, and `WEBP -> AVIF`
- `/health` and `/api/v1/capabilities` both reported `avif_available: true` during validation

This is the runtime currently treated as the trusted AVIF-capable environment for local and containerized development.

### What triggers AVIF detection

- `pillow-avif-plugin` Python package installed
- `libaom-dev` system library present (installed in the Docker container via apt)
- If either is missing, the API logs `Startup: AVIF=False` and AVIF is excluded from the capabilities response

### UI Safety Rule

The frontend should not advertise AVIF without confirmation from `/api/v1/capabilities`.
If the API is online but the capabilities request fails, the UI should fall back to `AVIF unavailable` rather than assuming support.

## Docker Compose Healthcheck Defaults

The `api` service in `docker-compose.yml` uses these healthcheck values:

| Setting | Value |
|---------|-------|
| `interval` | `30s` |
| `timeout` | `10s` |
| `retries` | `3` |
| `start_period` | `10s` |

The healthcheck polls `GET /health`. When `docker compose up -d` reports the `api` service as healthy, the endpoint returns `"status": "online"`.

## Configuration Matrix

| Variable | Affects web container | Affects api container | Notes |
|----------|----------------------|----------------------|-------|
| `VITE_API_BASE_URL` | ✅ (build-time) | ❌ | Frontend reads this at Vite build time via `import.meta.env`. Changes require a frontend rebuild. |
| `CORS_ORIGINS` | ❌ | ✅ | FastAPI reads this at startup. Changes require an API restart. |

## Relationship to `.env.example`

`.env.example` in the project root is the **copyable template** for local development. It contains the two variables currently recognized by the application:

```
VITE_API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

This document (`docs/environment.md`) is the **authoritative reference** for what each variable does, its default, and its effect. Use `.env.example` to get started; use this doc to understand what you're setting.

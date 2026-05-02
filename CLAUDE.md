# Asset Optimizer

## Project Definition

Asset Optimizer is a real web product focused on preparing images for websites, e-commerce, and digital products.

It is not just a generic format converter. The product value is helping users transform, compress, and resize image assets so they are ready for publishing with better performance, compatibility, and lower file size.

## Target Users

- People building websites
- E-commerce teams managing product images
- Creators preparing assets for digital products
- Developers and designers optimizing images for the web

## Product Positioning

Primary promise:

> Convert, compress, and adapt images for web and e-commerce in seconds.

## MVP v1 Scope

### Supported Input Formats
- JPG / JPEG
- PNG
- WEBP

### Supported Output Formats
- JPG / JPEG
- PNG
- WEBP
- AVIF

### Core Features
- Upload one or multiple image files
- Select an entire folder from the browser
- Convert between supported formats
- Adjust output quality / compression
- Resize by dimensions
- Show original vs optimized size
- Download a single transformed file
- Download batch transformations as a ZIP file

## Batch Processing Rules

- If the user uploads a single file, the app returns a direct file download.
- If the user uploads multiple files or a full folder, the app returns a ZIP file.
- Folder uploads should preserve relative paths when possible so the ZIP can maintain useful structure and avoid filename collisions.

## Technical Direction

### Monorepo Structure

```txt
asset-optimizer/
  apps/
    web/   # React + TypeScript frontend
    api/   # FastAPI backend
  docs/
  docker-compose.yml
  CLAUDE.md
```

### Frontend
- React
- TypeScript

Responsibilities:
- File and folder selection
- Transformation form UI
- Preview of files and optimization summary
- Download flow for single assets and ZIP results

### Backend
- Python
- FastAPI

Responsibilities:
- Receive uploads
- Validate files and limits
- Perform image transformations
- Package batch outputs as ZIP
- Return transformed asset or ZIP response

## Architecture Decision for v1

Processing should be synchronous in v1, with clear limits for file count and total upload size.

Reasoning:
- Faster MVP delivery
- Simpler backend architecture
- Enough for validating the product with real users

The code should still be organized so the processing pipeline can later evolve into asynchronous jobs for large batches.

The project should run locally through Docker Compose so both services can be started with a single command.

## Non-Goals for v1

- No advanced image editor
- No authentication unless product requirements change
- No heavy async job system on day one
- No support for many low-priority legacy formats in the first release

## Future Expansion Ideas

- Presets for e-commerce, hero banners, thumbnails, and Open Graph
- Batch rename
- Visual before/after comparison
- Background removal or transparency workflows
- Async processing jobs with progress tracking
- More formats when validated by user demand

## Versioning Policy

This project should follow Semantic Versioning (`MAJOR.MINOR.PATCH`), but it should remain in the `0.x` stage until the product contract and runtime behavior are considered stable.

### Current Versioning Philosophy

- `0.1.0` = first functional MVP
- `0.x` = active product shaping, contract still maturing
- `1.0.0` = first stable public-ready baseline

### How to Bump Versions

- `PATCH` (`0.1.1`) for bug fixes, UI fixes, validation fixes, and non-breaking internal improvements
- `MINOR` (`0.2.0`) for meaningful new capabilities that do not break expected behavior
- `MAJOR` (`1.0.0`, `2.0.0`) for breaking contract changes or for declaring a stable public release baseline

### Practical Guidance for This Project

- Do not jump to `1.0.0` just because the app works
- Stay in `0.x` while batch behavior, runtime AVIF support, and UX contracts are still evolving
- Promote to `1.0.0` only when the main user flows, API contract, and deployment/runtime behavior are trustworthy and intentionally stable

### Source of Truth

- Frontend package version currently lives in `apps/web/package.json`
- If backend versioning becomes externally relevant later, it should be aligned intentionally rather than ad hoc

## Product Principle

Users do not buy “10 formats.”
Users buy ready-to-publish assets with less weight, good quality, and better web performance.

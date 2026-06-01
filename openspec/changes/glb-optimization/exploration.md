# Exploration: GLB Weight Reduction Support

## Current State

Asset Optimizer is a synchronous image processing pipeline with a clean separation between frontend (React + TypeScript) and backend (FastAPI + Python).

**Image Pipeline (existing):**
- Input: JPG, JPEG, PNG, WEBP
- Output: JPG, PNG, WEBP, AVIF
- Processing: `apps/api/app/services/transform.py` uses PIL for decode → resize → normalize mode → encode
- Batch: Single file → direct download; Multiple files → ZIP with `manifest.json`
- Limits: 100 files, 50 MB total, 50 MP per image
- Response metadata: Original/optimized bytes, compression ratio, dimensions, format

**Key Architecture Patterns:**
- `ProcessedFile` dataclass tracks original vs optimized metadata
- `_build_single_response()` and `_build_zip_response()` construct responses with X-Asset-* headers
- `archive.py` handles ZIP creation with collision resolution and manifest embedding
- Frontend `useImageProcessing` hook handles both single-file and ZIP flows
- `ResultPanel` shows image comparison slider for single files, batch table for ZIPs

## Affected Areas

### Backend
- `apps/api/app/main.py` — Add GLB validation, new endpoint, reuse response builders
- `apps/api/app/schemas.py` — Add GLB-specific error codes
- `apps/api/app/services/transform.py` — Keep untouched (image-only)
- `apps/api/app/services/archive.py` — Reuse as-is (generic ZIP builder)
- `apps/api/Dockerfile` — **Node.js required** for gltf-transform CLI
- `apps/api/requirements.txt` — Add `pygltflib` for GLB parsing/validation (optional but useful)

### Frontend
- `apps/web/src/App.tsx` — Add GLB to `SUPPORTED_INPUT_FORMAT`, update `isSupportedInputFile()`
- `apps/web/src/components/SourcePanel.tsx` — Update `INPUT_ACCEPT` and format hint text
- `apps/web/src/components/SettingsPanel.tsx` — Add GLB-specific settings (compression method, texture compress)
- `apps/web/src/components/ResultPanel.tsx` — Skip image preview for GLB, show size comparison only
- `apps/web/src/hooks/useImageProcessing.ts` — Add GLB endpoint call path

### Infrastructure
- `docker-compose.yml` — May need updates if we split into a separate GLB service

## Approaches

### 1. Node.js Subprocess with gltf-transform CLI (Recommended)

Install Node.js in the API container and shell out to `@gltf-transform/cli`.

**Pros:**
- Industry-standard tool (1.9k GitHub stars, actively maintained by Don McCurdy)
- Supports all major optimizations: Draco, Meshopt, quantization, dedup, prune, texture compress
- Single command: `gltf-transform optimize input.glb output.glb --compress draco`
- Mature, well-tested, handles edge cases
- Can upgrade to more aggressive optimizations later without code changes

**Cons:**
- Requires Node.js in the Python container (Dockerfile changes)
- Subprocess overhead (~100-300ms spawn time)
- Adds ~100-200MB to container size with Node + npm packages
- Dependency on external CLI tool

**Effort:** Low-Medium

**Docker impact:**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && npm install -g @gltf-transform/cli \
    && rm -rf /var/lib/apt/lists/*
```

**Example usage:**
```python
import subprocess

subprocess.run([
    'gltf-transform', 'optimize',
    'input.glb', 'output.glb',
    '--compress', 'draco',
    '--texture-compress', 'webp',
    '--dedup', '--prune'
], check=True)
```

### 2. Pure Python with pygltflib + meshoptimizer

Use `pygltflib` to parse GLB and `meshoptimizer` Python bindings for vertex/index optimization.

**Pros:**
- No Node.js dependency — stays pure Python
- `pygltflib` is mature (v1.16.5) and supports full glTF spec
- Direct Python API — no subprocess overhead
- Smaller container size

**Cons:**
- `meshoptimizer` Python package is **alpha** (v0.2.30a0) and incomplete
- No built-in Draco compression support in Python ecosystem
- Would need to manually implement: dedup, prune, quantization pipeline
- Cannot compress embedded textures (a major source of GLB bloat)
- Significantly more code to write and maintain
- Less effective compression than gltf-transform

**Effort:** High

### 3. Separate Node.js Microservice

Run gltf-transform in a dedicated container/service, communicate via HTTP or shared volume.

**Pros:**
- Clean separation of concerns
- Python container stays lean
- Can scale GLB processing independently
- Fault isolation — GLB crashes don't affect image API

**Cons:**
- More infrastructure complexity
- Need service discovery / internal HTTP calls
- Slower due to network round-trip
- Overkill for MVP scope

**Effort:** Medium-High

### 4. Python with trimesh

Use `trimesh` library which can load GLB and has some simplification/export features.

**Pros:**
- Pure Python, well-established library
- Can load/export GLB

**Cons:**
- Not designed for glTF optimization — loses extensions, materials, animations
- No Draco, meshopt, or texture compression
- Would corrupt most real-world GLB files
- Essentially a non-starter for this use case

**Effort:** Medium (but poor results)

## Recommendation

**Use Approach 1: Node.js subprocess with gltf-transform CLI.**

Rationale:
1. **Best compression results** — Draco + texture compression can reduce GLB size by 50-90%
2. **Fastest to implement** — single subprocess call vs hundreds of lines of Python
3. **Future-proof** — can toggle optimization flags without code changes
4. **Industry standard** — gltf-transform is the de facto tool for this job
5. **Acceptable tradeoff** — Container size increase is acceptable for the capability gained

For the **MVP v1 of GLB support**, use conservative settings:
```bash
gltf-transform optimize input.glb output.glb \
  --dedup --prune --quantize \
  --compress draco \
  --texture-compress webp
```

This gives us:
- Deduplicate accessors and textures
- Remove unused nodes/materials
- Quantize geometry (reduce precision)
- Draco mesh compression
- WebP texture compression (major size win)

**No mesh simplification** — per user requirements, we only do weight reduction, not geometry reduction.

## API Design

**New endpoint:** `POST /api/v1/optimize-glb`

**Form fields:**
- `files: list[UploadFile]` — GLB files
- `compression: str` — `"draco" | "meshopt" | "none"` (default: "draco")
- `texture_compress: bool` — Enable WebP texture compression (default: true)
- `quantize: bool` — Enable geometry quantization (default: true)
- `zip_name, output_prefix, output_suffix, output_stem` — Same naming as /transform

**Response:** Same pattern as `/transform`:
- Single file: Direct GLB download with `X-Asset-Original-Bytes`, `X-Asset-Optimized-Bytes`, `X-Asset-Compression-Ratio`
- Multiple files: ZIP with `manifest.json`

**Schema additions:**
```python
class ErrorCode(str, Enum):
    # ... existing ...
    UNSUPPORTED_GLB_FORMAT = "UNSUPPORTED_GLB_FORMAT"
    GLB_TOO_LARGE = "GLB_TOO_LARGE"
    GLB_OPTIMIZATION_FAILED = "GLB_OPTIMIZATION_FAILED"
```

## Frontend Changes

**SourcePanel:**
- Add `.glb` to `INPUT_ACCEPT`
- Update format hints to mention GLB support

**SettingsPanel:**
- When GLB files selected, show GLB-specific settings:
  - Compression method: Draco / Meshopt / None
  - Texture compression: toggle
  - Quantization: toggle
- Hide image-specific settings (quality, output format, max width/height)

**ResultPanel:**
- For GLB single-file results: Skip image comparison slider, show file size comparison only
- Batch results: Reuse existing BatchResultPanel (no dimensions column for GLB)

**useImageProcessing:**
- Detect file type from selection
- Route to `/api/v1/transform` (images) or `/api/v1/optimize-glb` (GLB)
- Do not mix image and GLB files in same batch

## Architecture Fit

**Keep pipelines separate but DRY:**

```
apps/api/app/
  services/
    transform.py          # Image pipeline — UNCHANGED
    glb_optimizer.py      # NEW: GLB optimization service
    archive.py            # Reused for both
  main.py                 # Add /optimize-glb endpoint
```

**Shared utilities:**
- `archive.zip_transformed_assets()` — Already generic, works for any bytes
- Naming resolution (`resolve_single_output_name`, etc.) — Reuse as-is
- Limit checking (`_check_limits`) — Reuse with GLB-specific constants

**Batch processing:**
- Reuse exact same ZIP + manifest flow
- Manifest schema works for GLB (just omit dimension fields)

## Risks

1. **Docker complexity** — Installing Node.js in Python container adds build time and size. Mitigation: Use slim Node install, clean up apt cache.

2. **Subprocess blocking** — gltf-transform CLI could take seconds for large GLB files. Mitigation: Use `asyncio.create_subprocess_exec()` to avoid blocking the event loop. Add timeout handling.

3. **GLB validation** — Need to validate uploaded files are actually valid GLB before processing. Mitigation: Use `pygltflib` for lightweight validation (check magic bytes + JSON header), or let gltf-transform fail gracefully.

4. **Container size** — Node.js + npm packages add ~150MB. Mitigation: Acceptable for the capability; could optimize later with multi-stage builds.

5. **Mixed file types** — User might select images + GLB together. Mitigation: Frontend rejects mixed selections; or backend returns clear error.

6. **Texture compression failures** — Some GLB files have unusual texture formats. Mitigation: Make texture compression optional; fallback to geometry-only optimization on failure.

## Ready for Proposal

**Yes.** 

The orchestrator should tell the user:
- GLB optimization will use the industry-standard gltf-transform CLI via Node.js subprocess
- This requires adding Node.js to the API Docker container
- MVP scope: weight reduction only (Draco + quantization + texture compression), no mesh simplification
- Frontend can reuse most existing components with minor adaptations
- We need a new `/api/v1/optimize-glb` endpoint, keeping the image `/transform` endpoint completely untouched

**Next steps for proposal:**
1. Confirm Docker approach (Node.js in api container vs separate service)
2. Define exact GLB optimization settings for MVP
3. Approve frontend UX for GLB (settings panel changes, no 3D preview for MVP)
4. Define file size limits for GLB (suggest same 50MB total, maybe larger per-file limit)

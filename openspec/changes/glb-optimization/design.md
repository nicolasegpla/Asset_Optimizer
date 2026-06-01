# Design: GLB Weight Reduction Support

## Technical Approach

Add a parallel GLB optimization pipeline (new endpoint, service, runtime probe, frontend route) that coexists with the image pipeline without modifying it. GLB processing uses `gltf-transform` CLI invoked via `subprocess.run` with temporary files. Batch ZIP reuses `archive.py` unchanged. The frontend detects `.glb` files and routes to the GLB-specific hook/settings.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Shared endpoint vs new endpoint | New `POST /api/v1/optimize-glb` | Different validation (GLB magic vs PIL), limits (100MB vs image limits), processing model (subprocess vs PIL), and result schema (no dimensions). Mixing would bloat the transform endpoint. |
| Python GLB lib vs CLI subprocess | `gltf-transform` CLI via `subprocess.run` | No mature Python GLB optimization library. `gltf-transform` (JS) is the de facto standard. Subprocess avoids Python→Node.js IPC complexity for MVP. |
| GLB preview vs size-only | Size-only, no 3D preview | No preview library in project. Dimensions do not map to GLB. Size comparison is the primary value proposition. |
| Frontend hook reuse vs new hook | New `useGlbProcessing` hook | Image hook bakes in `/api/v1/transform`, image comparison previews, and dimension handling. A separate hook keeps concerns clean. |
| Fixed vs configurable GLB settings | Fixed MVP settings: `--dedup --prune --quantize --compress draco` | Simpler UI, faster delivery. Settings can become configurable in a follow-up. |

## Data Flow

```
Frontend                          API
  │                                │
  ├─ file select ──► type detect   │
  │   ├─ images  ──► /transform    │
  │   └─ .glb    ──► /optimize-glb │
  │                                │
  │  POST multipart/form-data ────►│
  │  { files[], quality? }         ├─ validate GLB magic/limit
  │                                ├─ subprocess: gltf-transform
  │                                │    input.glb → output.glb
  │                                ├─ single: Response(bytes)
  │  ◄── direct .glb or .zip ─────┤  └─ batch:  zip_transformed_assets()
  │                                │
  ├─ trigger download              │
  └─ show size comparison          │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/api/app/services/glb_optimizer.py` | Create | Pure functions: validate GLB magic bytes, run `gltf-transform` subprocess with temp files, return `(optimized_bytes, metadata)` |
| `apps/api/app/services/runtime.py` | Modify | Add `gltf_transform_available` field to `RuntimeProfile`, probe via `subprocess.run(["gltf-transform", "--version"])` |
| `apps/api/app/schemas.py` | Modify | Add error codes: `INVALID_GLB`, `GLB_TOO_LARGE`, `GLB_OPTIMIZATION_FAILED`, `GLB_RUNTIME_UNAVAILABLE`, `MIXED_FILE_TYPES` |
| `apps/api/app/main.py` | Modify | Add `POST /api/v1/optimize-glb` endpoint; add GLB constants (`MAX_GLB_PER_FILE=100*1024*1024`, `MAX_GLB_TOTAL=500*1024*1024`); expose GLB in `/health` |
| `apps/api/Dockerfile` | Modify | Add Node.js 22.x via `setup_22.x` from NodeSource, install `@gltf-transform/cli` globally |
| `apps/web/src/App.tsx` | Modify | Add `.glb` to `INPUT_ACCEPT`, add `SUPPORTED_GLB_EXTENSIONS`, detect file type and route to GLB hook |
| `apps/web/src/hooks/useGlbProcessing.ts` | Create | Builds FormData, calls `/api/v1/optimize-glb`, handles single/zip download (no preview) |
| `apps/web/src/components/SourcePanel.tsx` | Modify | Update accept attribute to `.jpg,.jpeg,.png,.webp,.glb`; update format hints |
| `apps/web/src/components/SettingsPanel.tsx` | Modify | Hide quality/dimensions for GLB-only selections (show GLB label instead) |
| `apps/web/src/components/ResultPanel.tsx` | Modify | For GLB results: show size comparison only, no image preview panel |

## Interfaces / Contracts

```python
# glb_optimizer.py — pure functions, mirrors transform.py pattern

@dataclass(frozen=True)
class GlbOptimizationMetadata:
    original_bytes: int
    optimized_bytes: int
    compression_ratio: float

def validate_glb_magic(data: bytes) -> None:
    """Raise ValueError if data does not start with 'glTF' magic (offset 0)."""

def optimize_glb(data: bytes) -> tuple[bytes, GlbOptimizationMetadata]:
    """Run gltf-transform subprocess chain, return optimized bytes + metadata."""
```

```python
# main.py — new endpoint signature

@app.post("/api/v1/optimize-glb")
async def optimize_glb_assets(
    request: Request,
    files: list[UploadFile] = File(...),
    paths: str | None = Form(default=None),
    zip_name: str | None = Form(default=None),
    output_prefix: str | None = Form(default=None),
    output_suffix: str | None = Form(default=None),
    output_stem: str | None = Form(default=None),
) -> Response:
    # Rejects mixed file types (GLB + non-GLB)
    # Single file → direct .glb download
    # Multiple GLBs → ZIP with manifest.json
```

```typescript
// useGlbProcessing.ts — frontend hook

interface GlbOptimizeOptions {
    files: File[];
    zipName?: string;
    outputPrefix?: string;
    outputSuffix?: string;
    outputStem?: string;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `validate_glb_magic` with valid/corrupt/missing magic bytes | `pytest` parametrized, in-memory GLB binary fixtures |
| Unit | `optimize_glb` subprocess invocation, timeout handling | `pytest` with `subprocess` mock; integration test against real CLI in Docker |
| Unit | Runtime probe returns correct `gltf_transform_available` | Mock subprocess success/failure |
| Integration | `POST /api/v1/optimize-glb` single GLB, batch GLB, mixed rejection, oversized rejection | `httpx` + `TestClient`, generate minimal GLB fixtures |
| Integration | Batch ZIP response includes `manifest.json` with GLB entries | Verify ZIP content + manifest schema |
| E2E | Frontend GLB file selection → settings → download single/ZIP | Not in MVP — manual smoke test with real GLB files |

## Migration / Rollout

No migration required. The image pipeline is untouched. The `/health` endpoint gains a `gltf_transform_available` field. If `gltf-transform` is not installed at runtime, the GLB endpoint returns `GLB_RUNTIME_UNAVAILABLE` (mirrors AVIF guard pattern).

## Open Questions

- [ ] Do we need separate batch limits for GLB (count, total MB) or reuse `MAX_FILES` / `MAX_TOTAL_BYTES` with a higher size cap?

# Proposal: GLB Weight Reduction Support

## Intent

Enable Asset Optimizer to accept `.glb` 3D model files and reduce their file size through mesh compression, quantization, and texture compression. Users need ready-to-publish 3D assets with lower weight for web and e-commerce, matching the same product promise as image optimization.

## Scope

### In Scope
- New `POST /api/v1/optimize-glb` endpoint
- GLB file validation (magic bytes, size limits)
- Node.js subprocess calling `gltf-transform optimize` CLI
- Dockerfile changes: install Node.js + `@gltf-transform/cli` in API container
- Frontend: accept `.glb` files, route to GLB endpoint, show size-only results
- Batch processing: ZIP output with `manifest.json` (reuse existing archive.py)
- GLB-specific settings: compression method (draco/meshopt), texture compression toggle, quantization toggle

### Out of Scope
- Mesh simplification / decimation (geometry reduction)
- 3D preview or model viewer in frontend
- Mixed batches (images + GLB in same upload)
- Additional 3D formats (gltf, fbx, obj) — GLB only for MVP
- Async job queue — still synchronous processing

## Capabilities

> Contract with sdd-spec. No existing specs found — all capabilities are new.

### New Capabilities
- `glb-optimization`: Upload GLB files, apply weight reduction (Draco/meshopt compression, quantization, texture compression), download optimized output. Covers endpoint, validation, subprocess service, and frontend routing.
- `glb-batch-processing`: Batch GLB uploads produce ZIP with preserved structure and manifest.json. Reuses existing archive patterns.

### Modified Capabilities
- None — image transformation pipeline (`image-transform`) remains completely untouched.

## Approach

**Node.js subprocess with `gltf-transform` CLI** inside the existing API container.

```
gltf-transform optimize input.glb output.glb \
  --dedup --prune --quantize \
  --compress draco \
  --texture-compress webp
```

- New service file `apps/api/app/services/glb_optimizer.py` handles subprocess invocation with `asyncio.create_subprocess_exec()`
- Validation: check `.glb` extension, 100 MB per-file limit, magic bytes (`glTF`)
- Frontend detects file type from selection, routes to correct endpoint, hides image-specific settings
- `ResultPanel` skips image comparison for GLB, shows file size comparison only

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/app/main.py` | New | Add `/optimize-glb` endpoint with validation |
| `apps/api/app/services/glb_optimizer.py` | New | GLB optimization subprocess service |
| `apps/api/app/schemas.py` | Modified | Add GLB error codes |
| `apps/api/Dockerfile` | Modified | Install Node.js + gltf-transform CLI |
| `apps/web/src/App.tsx` | Modified | Add GLB to supported formats |
| `apps/web/src/components/SourcePanel.tsx` | Modified | Accept `.glb` files |
| `apps/web/src/components/SettingsPanel.tsx` | Modified | GLB-specific settings panel |
| `apps/web/src/components/ResultPanel.tsx` | Modified | Skip image preview for GLB |
| `apps/web/src/hooks/useImageProcessing.ts` | Modified | Route GLB to new endpoint |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Docker image grows ~150MB with Node.js | High | Acceptable tradeoff; optimize later with multi-stage builds |
| Subprocess blocks event loop | Medium | Use `asyncio.create_subprocess_exec()` + timeout |
| Invalid GLB files cause silent failures | Medium | Validate magic bytes before processing; catch subprocess errors |
| User uploads mixed images + GLB | Medium | Frontend rejects mixed selections; backend returns clear error |
| Texture compression fails on unusual formats | Low | Make texture compression optional; fallback to geometry-only |

## Rollback Plan

1. Remove `/optimize-glb` endpoint from `main.py`
2. Delete `apps/api/app/services/glb_optimizer.py`
3. Revert `Dockerfile` Node.js installation
4. Revert frontend format acceptance changes
5. Image pipeline (`/transform`) remains untouched throughout — zero impact on existing functionality

## Dependencies

- Node.js 18+ installed in API Docker container
- `@gltf-transform/cli` installed globally via npm
- `pygltflib` (optional, for lightweight GLB validation)

## Success Criteria

- [ ] Single GLB file uploads return optimized GLB with size reduction headers
- [ ] Batch GLB uploads return ZIP with manifest.json
- [ ] Image `/transform` endpoint continues working unchanged (regression test)
- [ ] Frontend correctly routes GLB vs image files to respective endpoints
- [ ] Invalid/non-GLB files rejected with clear error message
- [ ] Docker build succeeds with Node.js + gltf-transform installed

# Tasks: GLB Weight Reduction Support

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500–600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend/Dockerfile) → PR 2 (frontend) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main|feature-branch-chain|size-exception|pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend foundation + API endpoint | PR 1 | Dockerfile, glb_optimizer service, schemas, main.py endpoint |
| 2 | Frontend integration | PR 2 | useGlbProcessing hook, App routing, SourcePanel, SettingsPanel, ResultPanel |

## Phase 1: Infrastructure / Foundation

- [x] 1.1 `apps/api/Dockerfile` — Add NodeSource `setup_22.x`, install `@gltf-transform/cli` globally
- [x] 1.2 `apps/api/app/services/glb_optimizer.py` — Create `GlbOptimizationMetadata` dataclass, `validate_glb_magic()`, `optimize_glb()` with temp files and subprocess

## Phase 2: API Layer

- [x] 2.1 `apps/api/app/schemas.py` — Add error codes: `INVALID_GLB`, `GLB_TOO_LARGE`, `GLB_OPTIMIZATION_FAILED`, `GLB_RUNTIME_UNAVAILABLE`, `MIXED_FILE_TYPES`
- [x] 2.2 `apps/api/app/services/runtime.py` — Add `gltf_transform_available` to `RuntimeProfile`, probe via `subprocess.run(["gltf-transform", "--version"])`
- [x] 2.3 `apps/api/app/main.py` — Add `POST /api/v1/optimize-glb` endpoint, constants `MAX_GLB_PER_FILE=100MB`, `MAX_GLB_TOTAL=50MB` per batch; expose GLB in `/health`

## Phase 3: Frontend Core

- [x] 3.1 `apps/web/src/hooks/useGlbProcessing.ts` — New hook: builds `FormData`, calls `/api/v1/optimize-glb`, handles single `.glb` and batch ZIP download
- [x] 3.2 `apps/web/src/App.tsx` — Add `.glb` to `INPUT_ACCEPT`, add `SUPPORTED_GLB_EXTENSIONS`, detect file type and route to GLB hook

## Phase 4: Frontend Components

- [x] 4.1 `apps/web/src/components/SourcePanel.tsx` — Update accept attribute to `.jpg,.jpeg,.png,.webp,.glb`
- [x] 4.2 `apps/web/src/components/SettingsPanel.tsx` — Hide quality/dimensions for GLB-only selections, show GLB label
- [x] 4.3 `apps/web/src/components/ResultPanel.tsx` — For GLB results: show size comparison only, no image preview

## Phase 5: Testing / Verification

- [x] 5.1 `apps/api/tests/test_glb_optimizer.py` — Test `validate_glb_magic` with valid/corrupt/missing magic bytes (parametrized `pytest`)
- [x] 5.2 `apps/api/tests/test_glb_endpoint.py` — Integration tests: single GLB, batch GLB, mixed rejection, oversized rejection using `httpx` + `TestClient`
- [x] 5.3 `apps/web/src/hooks/__tests__/useGlbProcessing.test.ts` — Unit test for hook with file list and zip handling
- [ ] 5.4 Verify Docker compose builds and `/health` shows `gltf_transform_available`
# glb-optimization Specification

## Purpose

Define the user-visible contract for single GLB optimization without changing the existing image pipeline.

## Requirements

### Requirement: Single GLB optimization contract

The system MUST accept `POST /api/v1/optimize-glb` for one or more GLB uploads and, for a single GLB file, return one optimized `.glb` download with size metadata headers.

#### Scenario: Single GLB succeeds

- GIVEN one valid GLB file and supported optimization settings
- WHEN the client submits `POST /api/v1/optimize-glb`
- THEN the response is a direct `.glb` download
- AND the response includes original-bytes, optimized-bytes, and compression-ratio headers

### Requirement: GLB validation and request safety

The system MUST reject files that are not valid GLB uploads, exceed configured GLB limits, or are mixed with non-GLB files in the same request.

#### Scenario: Invalid file is rejected

- GIVEN an upload with a wrong extension or invalid GLB signature
- WHEN the request is submitted
- THEN the system rejects the file with a clear GLB validation error

#### Scenario: Oversized GLB is rejected

- GIVEN a GLB file above the configured per-file limit
- WHEN the request is submitted
- THEN the system rejects the upload before optimization starts

### Requirement: Optimization execution and failure reporting

The system MUST run GLB optimization within a bounded execution window, report optimization failures clearly, and leave the image `/transform` capability untouched.

#### Scenario: Optimization completes within limits

- GIVEN a valid GLB file and supported settings
- WHEN optimization is executed
- THEN the system returns the optimized file in the same request cycle

#### Scenario: Optimization times out or fails

- GIVEN a valid GLB file that cannot be optimized successfully
- WHEN processing exceeds the allowed window or the optimizer fails
- THEN the system returns a clear optimization error without partial output

### Requirement: GLB-specific user flow and runtime readiness

The system MUST expose GLB-specific settings in the frontend, show size-only results for GLB outputs, and ensure the API runtime is prepared to serve GLB optimization requests.

#### Scenario: Frontend adapts to GLB selection

- GIVEN the user selects GLB files only
- WHEN the upload flow enters settings and results
- THEN the UI shows GLB optimization options and hides image-only controls
- AND the result view shows size comparison without image preview

#### Scenario: Runtime is not ready

- GIVEN the GLB optimization runtime dependency is unavailable
- WHEN a GLB optimization request is received
- THEN the system returns a clear service failure instead of silently falling back

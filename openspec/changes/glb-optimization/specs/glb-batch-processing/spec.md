# glb-batch-processing Specification

## Purpose

Define the user-visible contract for optimizing multiple GLB files in one synchronous batch.

## Requirements

### Requirement: Homogeneous GLB batch acceptance

The system MUST accept batch optimization only when every uploaded file is a valid GLB and SHALL reject mixed image/GLB selections.

#### Scenario: GLB batch is accepted

- GIVEN multiple valid GLB files in one request
- WHEN the client submits batch optimization
- THEN the system starts one GLB batch workflow for the full set

#### Scenario: Mixed batch is rejected

- GIVEN a request containing at least one GLB and one non-GLB file
- WHEN the batch is submitted
- THEN the system rejects the request with a clear mixed-file-type error

### Requirement: ZIP response with manifest

The system MUST return batch GLB results as a ZIP archive containing optimized files and a `manifest.json` that describes the batch outcome.

#### Scenario: Batch ZIP is returned

- GIVEN a batch with more than one valid GLB file
- WHEN optimization completes successfully
- THEN the response is a ZIP download
- AND the ZIP contains the optimized GLB outputs and `manifest.json`

#### Scenario: Relative structure is preserved

- GIVEN files uploaded from nested browser folders
- WHEN the batch ZIP is produced
- THEN the archive preserves useful relative paths or collision-safe names for each output

### Requirement: Batch manifest and result reporting

The manifest MUST describe each processed GLB entry with enough metadata for the frontend or user to understand the batch result, including size outcomes and failures when present.

#### Scenario: Manifest records successful entries

- GIVEN a successful GLB batch
- WHEN `manifest.json` is generated
- THEN each entry includes the source identity, output identity, and size outcome

#### Scenario: Manifest records per-file failure

- GIVEN a batch where one GLB cannot be optimized
- WHEN the batch result is finalized
- THEN the manifest records the failed entry with a clear failure reason

### Requirement: Synchronous batch limits and user feedback

The system MUST enforce configured batch limits and the frontend SHOULD present GLB batch results through the existing download-oriented flow.

#### Scenario: Batch exceeds allowed limits

- GIVEN a GLB batch above the configured count or total-size limits
- WHEN the request is submitted
- THEN the system rejects the batch with a clear limit error

#### Scenario: Frontend presents batch result

- GIVEN a successful GLB batch response
- WHEN the user reviews the result
- THEN the UI offers the ZIP download and summarizes size reduction outcomes

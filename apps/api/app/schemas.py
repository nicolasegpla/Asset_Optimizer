"""Shared schemas for error payloads and internal metadata contracts."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    UNSUPPORTED_INPUT_FORMAT = "UNSUPPORTED_INPUT_FORMAT"
    UNSUPPORTED_OUTPUT_FORMAT = "UNSUPPORTED_OUTPUT_FORMAT"
    INVALID_IMAGE = "INVALID_IMAGE"
    INVALID_DIMENSIONS = "INVALID_DIMENSIONS"
    INVALID_QUALITY = "INVALID_QUALITY"
    FILE_COUNT_LIMIT = "FILE_COUNT_LIMIT"
    TOTAL_SIZE_LIMIT = "TOTAL_SIZE_LIMIT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    INVALID_PATHS_FORMAT = "INVALID_PATHS_FORMAT"


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, object] | None = Field(default=None)


class ErrorPayload(BaseModel):
    error: ErrorDetail


class LimitsResponse(BaseModel):
    max_files: int
    max_total_bytes: int
    max_pixels: int


# ─── Batch manifest / partial-success schemas ──────────────────────────────────


class BatchManifestFile(BaseModel):
    source: str
    output: str
    originalBytes: int
    optimizedBytes: int
    compressionRatio: float
    originalFormat: str
    outputFormat: str
    originalDimensions: dict[str, int]
    outputDimensions: dict[str, int]


class BatchFileError(BaseModel):
    source: str
    code: ErrorCode
    message: str


class BatchManifestSummary(BaseModel):
    totalFiles: int
    processedFiles: int
    failedFiles: int
    totalOriginalBytes: int
    totalOptimizedBytes: int


class BatchManifest(BaseModel):
    files: list[BatchManifestFile]
    errors: list[BatchFileError]
    summary: BatchManifestSummary


class BatchAllFailDetails(BaseModel):
    totalFiles: int
    failedFiles: int
    errors: list[BatchFileError]


class BatchAllFailPayload(BaseModel):
    error: ErrorDetail

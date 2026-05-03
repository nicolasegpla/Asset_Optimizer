"""Asset Optimizer API — FastAPI application."""
from __future__ import annotations

import io
import logging
import time
import uuid
from collections.abc import Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.schemas import (
    BatchAllFailPayload,
    BatchFileError,
    BatchManifestFile,
    BatchManifestSummary,
    ErrorCode,
    ErrorDetail,
    ErrorPayload,
    LimitsResponse,
)
from app.services.archive import ArchivedFile, zip_transformed_assets
from app.services.runtime import build_runtime_profile, RuntimeProfile
from app.services.upload_paths import resolve_upload_paths
from app.services.transform import (
    OutputFormat,
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS,
    transform_image,
)
from app.services.naming import NamingConfig, resolve_single_output_name, resolve_batch_output_name, resolve_zip_name, sanitize_naming_config

# ─── Logging ───────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_FILES = 100
MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_PIXELS = 50 * 1024 * 1024  # 50 megapixels
PROCESSING_TIMEOUT_SECONDS = 120

DEFAULT_CORS_ORIGINS = (
    'http://localhost:5173',
    'http://127.0.0.1:5173',
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_extension(filename: str) -> str:
    suffix = filename.rsplit(".", maxsplit=1)[-1].lower()
    return suffix


def _replace_extension(path: str, output_format: OutputFormat) -> str:
    base_path, _ = os.path.splitext(path)
    extension = 'jpeg' if output_format == OutputFormat.JPG else output_format.value
    return f'{base_path}.{extension}'


def _count_bytes(files: Iterable[UploadFile]) -> int:
    total = 0
    for file in files:
        total += getattr(file, "size", 0) or 0
    return total


def _raise_error(code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> None:
    raise HTTPException(
        status_code=422,
        detail=ErrorPayload(error=ErrorDetail(code=code, message=message, details=details)).model_dump(mode="json"),
    )


def _try_validate_file(file: UploadFile, data: bytes) -> BatchFileError | None:
    """
    Validate a single file's format, dimensions, and content.
    Returns a BatchFileError if validation fails, or None if it passes.
    Does NOT raise — caller collects errors instead.
    """
    ext = _normalize_extension(file.filename or "")
    if ext not in SUPPORTED_INPUT_FORMATS:
        return BatchFileError(
            source=file.filename or "unknown",
            code=ErrorCode.UNSUPPORTED_INPUT_FORMAT,
            message=f"File '{file.filename}' has unsupported format '{ext}'.",
        )

    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            pixels = width * height
            if pixels > MAX_PIXELS:
                return BatchFileError(
                    source=file.filename or "unknown",
                    code=ErrorCode.IMAGE_TOO_LARGE,
                    message=f"Image '{file.filename}' exceeds {MAX_PIXELS // 1024**2} MP limit.",
                )
    except Exception:
        return BatchFileError(
            source=file.filename or "unknown",
            code=ErrorCode.INVALID_IMAGE,
            message=f"File '{file.filename}' is corrupt or not a valid image.",
        )
    return None


async def _read_upload_file(file: UploadFile) -> bytes:
    """Read all bytes from an UploadFile."""
    return await file.read()


def _check_limits(files: list[UploadFile], total_bytes: int) -> None:
    """Enforce hard limits on file count and total size."""
    if len(files) > MAX_FILES:
        _raise_error(
            ErrorCode.FILE_COUNT_LIMIT,
            f"Too many files. Maximum allowed is {MAX_FILES}.",
            {"max_files": MAX_FILES, "received": len(files)},
        )

    if total_bytes > MAX_TOTAL_BYTES:
        _raise_error(
            ErrorCode.TOTAL_SIZE_LIMIT,
            f"Total upload size exceeds {MAX_TOTAL_BYTES // (1024*1024)} MB limit.",
            {"max_bytes": MAX_TOTAL_BYTES, "received_bytes": total_bytes},
        )


def _validate_single_file(file: UploadFile, data: bytes) -> None:
    """Validate a single file's format, dimensions, and content."""
    ext = _normalize_extension(file.filename or "")
    if ext not in SUPPORTED_INPUT_FORMATS:
        _raise_error(
            ErrorCode.UNSUPPORTED_INPUT_FORMAT,
            f"File '{file.filename}' has unsupported format '{ext}'.",
            {"filename": file.filename, "received_format": ext},
        )

    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            pixels = width * height
            if pixels > MAX_PIXELS:
                _raise_error(
                    ErrorCode.IMAGE_TOO_LARGE,
                    f"Image '{file.filename}' exceeds {MAX_PIXELS // 1024**2} MP limit.",
                    {
                        "filename": file.filename,
                        "width": width,
                        "height": height,
                        "pixels": pixels,
                        "max_pixels": MAX_PIXELS,
                    },
                )
    except Exception:
        _raise_error(
            ErrorCode.INVALID_IMAGE,
            f"File '{file.filename}' is corrupt or not a valid image.",
            {"filename": file.filename},
        )


@dataclass
class ProcessedFile:
    relative_path: str
    filename: str
    data: bytes
    original_format: str
    original_height: int
    original_bytes: int
    original_width: int
    optimized_bytes: int
    compression_ratio: float
    transformed_height: int | None
    transformed_width: int | None


def _build_single_response(result: ProcessedFile, output_format: OutputFormat) -> Response:
    """Build a single-file download response with compression headers."""
    ext = output_format.value
    mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "Content-Type": mime,
        "X-Asset-Original-Bytes": str(result.original_bytes),
        "X-Asset-Optimized-Bytes": str(result.optimized_bytes),
        "X-Asset-Compression-Ratio": f"{result.compression_ratio:.2f}",
        "X-Asset-Original-Format": result.original_format,
        "X-Asset-Output-Format": output_format.value,
        "X-Asset-Original-Width": str(result.original_width),
        "X-Asset-Original-Height": str(result.original_height),
        "X-Asset-Output-Width": str(result.transformed_width or result.original_width),
        "X-Asset-Output-Height": str(result.transformed_height or result.original_height),
    }
    return Response(content=result.data, media_type=mime, headers=headers)


def _build_zip_response(
    zip_data: bytes,
    processed_count: int,
    original_bytes: int,
    optimized_bytes: int,
    zip_filename: str,
    error_count: int = 0,
) -> Response:
    """Build a batch ZIP download response with summary headers."""
    headers = {
        "Content-Disposition": f'attachment; filename="{zip_filename}"',
        "Content-Type": "application/zip",
        "X-Asset-Processed-Count": str(processed_count),
        "X-Asset-Original-Bytes": str(original_bytes),
        "X-Asset-Optimized-Bytes": str(optimized_bytes),
    }
    if error_count > 0:
        headers["X-Asset-Error-Count"] = str(error_count)
    return Response(content=zip_data, media_type="application/zip", headers=headers)


def _build_manifest_payload(
    processed: list[ProcessedFile],
    resolved_paths: list[str],
    batch_errors: list[BatchFileError],
) -> dict:
    """Build the manifest.json dict for a batch ZIP."""
    manifest_files = []
    for p, resolved_path in zip(processed, resolved_paths):
        ext = p.filename.rsplit(".", 1)[-1]
        output_format_val = "jpeg" if ext == "jpeg" else ext
        manifest_files.append({
            "source": p.filename,
            "output": resolved_path,
            "originalBytes": p.original_bytes,
            "optimizedBytes": p.optimized_bytes,
            "compressionRatio": round(p.compression_ratio, 4),
            "originalFormat": p.original_format,
            "outputFormat": output_format_val,
            "originalDimensions": {"width": p.original_width, "height": p.original_height},
            "outputDimensions": {
                "width": p.transformed_width or p.original_width,
                "height": p.transformed_height or p.original_height,
            },
        })

    manifest_errors = [
        {"source": e.source, "code": e.code.value, "message": e.message}
        for e in batch_errors
    ]

    total_original = sum(p.original_bytes for p in processed)
    total_optimized = sum(p.optimized_bytes for p in processed)
    total_files = len(processed) + len(batch_errors)

    return {
        "files": manifest_files,
        "errors": manifest_errors,
        "summary": {
            "totalFiles": total_files,
            "processedFiles": len(manifest_files),
            "failedFiles": len(manifest_errors),
            "totalOriginalBytes": total_original,
            "totalOptimizedBytes": total_optimized,
        },
    }


# ─── App lifecycle ─────────────────────────────────────────────────────────────

import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build runtime profile at startup, store in app.state."""
    profile = build_runtime_profile()
    app.state.runtime_profile = profile
    yield


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Asset Optimizer API", version="0.5.0", lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Assign request ID, log start/end with timing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()
    logger.info(
        "request_start: request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000)
    logger.info(
        "request_end: request_id=%s status_code=%s duration_ms=%s",
        request_id,
        response.status_code,
        duration_ms,
    )
    return response


cors_origins = os.getenv('CORS_ORIGINS')
allowed_origins = [origin.strip() for origin in cors_origins.split(',')] if cors_origins else list(DEFAULT_CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=[
        'Content-Disposition',
        'X-Asset-Original-Bytes',
        'X-Asset-Optimized-Bytes',
        'X-Asset-Compression-Ratio',
        'X-Asset-Processed-Count',
        'X-Asset-Error-Count',
        'X-Asset-Original-Format',
        'X-Asset-Output-Format',
        'X-Asset-Original-Width',
        'X-Asset-Original-Height',
        'X-Asset-Output-Width',
        'X-Asset-Output-Height',
    ],
)


@app.get("/health")
async def healthcheck(request: Request) -> dict[str, Any]:
    profile: RuntimeProfile | None = getattr(request.app.state, "runtime_profile", None)
    if profile is None:
        # Fallback for TestClient (lifespan not run) — probe now
        from app.services.runtime import build_runtime_profile
        profile = build_runtime_profile()
    return {
        "status": "online",
        "service": "asset-optimizer-api",
        "avif_available": profile.avif_available,
        "dependencies": {
            "pillow": {
                "version": profile.pillow_version,
                "status": "ok",
            },
            "avif_encoder": {
                "available": profile.avif_available,
                "status": "ok" if profile.avif_available else "unavailable",
            },
        },
    }


@app.get("/api/v1/capabilities")
async def get_capabilities(request: Request) -> dict[str, Any]:
    profile: RuntimeProfile | None = getattr(request.app.state, "runtime_profile", None)
    if profile is None:
        from app.services.runtime import build_runtime_profile
        profile = build_runtime_profile()
    output_formats = list(SUPPORTED_OUTPUT_FORMATS)
    if not profile.avif_available:
        output_formats = [f for f in output_formats if f != "avif"]
    return {
        "output_formats": output_formats,
        "avif_available": profile.avif_available,
    }


@app.get("/api/v1/formats")
async def list_formats() -> dict[str, list[str]]:
    return {
        "input_formats": list(SUPPORTED_INPUT_FORMATS),
        "output_formats": list(SUPPORTED_OUTPUT_FORMATS),
    }


@app.get("/api/v1/limits")
async def get_limits() -> LimitsResponse:
    return LimitsResponse(
        max_files=MAX_FILES,
        max_total_bytes=MAX_TOTAL_BYTES,
        max_pixels=MAX_PIXELS,
    )


@app.post("/api/v1/transform")
async def transform_assets(
    request: Request,
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    quality: int = Form(...),
    max_width: int | None = Form(default=None),
    max_height: int | None = Form(default=None),
    paths: str | None = Form(default=None),
    zip_name: str | None = Form(default=None),
    output_prefix: str | None = Form(default=None),
    output_suffix: str | None = Form(default=None),
    output_stem: str | None = Form(default=None),
) -> Response:
    """
    Transform one or more images: resize, convert format, compress.
    Single file → direct download. Multiple files → ZIP.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # ── Parse and validate output format ─────────────────────────────────────
    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError:
        _raise_error(
            ErrorCode.UNSUPPORTED_OUTPUT_FORMAT,
            f"Output format '{output_format}' is not supported.",
            {"received": output_format, "supported": list(SUPPORTED_OUTPUT_FORMATS)},
        )

    # ── AVIF runtime guard ────────────────────────────────────────────────────
    profile: RuntimeProfile | None = getattr(request.app.state, "runtime_profile", None)
    if profile is None:
        from app.services.runtime import build_runtime_profile
        profile = build_runtime_profile()
    if fmt == OutputFormat.AVIF and not profile.avif_available:
        _raise_error(
            ErrorCode.AVIF_UNAVAILABLE,
            "AVIF encoding is not available in this runtime environment.",
            {"avif_available": False},
        )

    # ── Validate quality ─────────────────────────────────────────────────────
    if not (1 <= quality <= 100):
        _raise_error(
            ErrorCode.INVALID_QUALITY,
            "Quality must be between 1 and 100.",
            {"received": quality},
        )

    # ── Validate dimensions ──────────────────────────────────────────────────
    if max_width is not None and not (1 <= max_width <= 10000):
        _raise_error(ErrorCode.INVALID_DIMENSIONS, "max_width must be between 1 and 10000.")
    if max_height is not None and not (1 <= max_height <= 10000):
        _raise_error(ErrorCode.INVALID_DIMENSIONS, "max_height must be between 1 and 10000.")

    # ── Validate naming config ───────────────────────────────────────────────
    try:
        naming_config = sanitize_naming_config(zip_name, output_prefix, output_suffix, output_stem)
    except ValueError as e:
        _raise_error(
            ErrorCode.INVALID_NAMING_CONFIG,
            f"Invalid naming field: {e}",
        )

    # ── Enforce hard limits ──────────────────────────────────────────────────
    total_bytes = _count_bytes(files)
    _check_limits(files, total_bytes)

    if not files:
        _raise_error(ErrorCode.FILE_COUNT_LIMIT, "No files provided.", {"max_files": MAX_FILES, "received": 0})

    # ── Read all file bytes and validate (per-file, collect errors) ──────────
    file_data_pairs: list[tuple[UploadFile, bytes]] = []
    batch_errors: list[BatchFileError] = []

    for f in files:
        data = await _read_upload_file(f)
        err = _try_validate_file(f, data)
        if err is not None:
            batch_errors.append(err)
        else:
            file_data_pairs.append((f, data))

    # All files failed validation → 422 with per-file error list (no ZIP)
    if not file_data_pairs and batch_errors:
        all_fail_payload = BatchAllFailPayload(
            error=ErrorDetail(
                code=ErrorCode.INVALID_IMAGE,
                message=f"All {len(files)} files failed processing.",
                details={
                    "totalFiles": len(files),
                    "failedFiles": len(batch_errors),
                    "errors": [e.model_dump() for e in batch_errors],
                },
            )
        )
        raise HTTPException(status_code=422, detail=all_fail_payload.model_dump(mode="json"))

    # ── Resolve folder-structure paths (optional) ─────────────────────────────
    resolved_paths: list[str] | None = None
    if paths is not None:
        resolved_paths = resolve_upload_paths(files, paths)

    # ── Process files (per-file try/except, collect successes and failures) ──
    start_time = time.monotonic()
    processed: list[ProcessedFile] = []
    processed_original = 0
    processed_optimized = 0
    transform_errors: list[BatchFileError] = []

    for idx, (file, data) in enumerate(file_data_pairs):
        elapsed = time.monotonic() - start_time
        if elapsed > PROCESSING_TIMEOUT_SECONDS:
            # Mark remaining files as timeout errors
            for remaining_file, _ in file_data_pairs[idx:]:
                transform_errors.append(
                    BatchFileError(
                        source=remaining_file.filename or "unknown",
                        code=ErrorCode.PROCESSING_TIMEOUT,
                        message="Processing timed out. Try fewer or smaller files.",
                    )
                )
            break

        # Use resolved path if provided, otherwise fall back to webkitRelativePath/filename
        if resolved_paths is not None:
            source_relative_path = resolved_paths[idx]
        else:
            source_relative_path = getattr(file, "webkitRelativePath", "") or file.filename or "unknown"

        source_filename = file.filename or "unknown"
        relative_path = _replace_extension(source_relative_path, fmt)
        filename = _replace_extension(source_filename, fmt)

        # Apply single-file naming: preserves original basename + prefix/suffix, no numbering.
        # (batch numbering is applied after the loop once we know the final count)
        relative_path = resolve_single_output_name(relative_path, naming_config, fmt.value)
        filename = resolve_single_output_name(filename, naming_config, fmt.value)

        # Per-file DEBUG start log
        logger.debug(
            "transform_start: request_id=%s filename=%s output_format=%s original_bytes=%s",
            request_id,
            source_filename,
            fmt.value,
            len(data),
        )

        try:
            transformed_data, metadata = transform_image(
                data=data,
                output_format=fmt,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
            )
        except Exception as e:
            # Per-file ERROR log
            logger.error(
                "transform_error: request_id=%s filename=%s format=%s error=%s",
                request_id,
                source_filename,
                fmt.value,
                str(e),
            )
            transform_errors.append(
                BatchFileError(
                    source=source_filename,
                    code=ErrorCode.INVALID_IMAGE,
                    message=f"Failed to transform '{source_filename}': {e}",
                )
            )
            continue

        # Per-file DEBUG completion log
        duration_ms = round((time.monotonic() - start_time) * 1000)
        logger.debug(
            "transform_end: request_id=%s filename=%s duration_ms=%s optimized_bytes=%s compression_ratio=%.2f",
            request_id,
            source_filename,
            duration_ms,
            metadata.optimized_bytes,
            metadata.compression_ratio,
        )

        processed.append(
            ProcessedFile(
                relative_path=relative_path,
                filename=filename,
                data=transformed_data,
                original_format=metadata.original_format,
                original_height=metadata.original_height,
                original_bytes=metadata.original_bytes,
                original_width=metadata.original_width,
                optimized_bytes=metadata.optimized_bytes,
                compression_ratio=metadata.compression_ratio,
                transformed_height=metadata.transformed_height,
                transformed_width=metadata.transformed_width,
            )
        )
        processed_original += metadata.original_bytes
        processed_optimized += metadata.optimized_bytes

    # ── Apply batch sequential naming ──────────────────────────────────────────
    # For batch/folder outputs: replace ALL basenames with {stem}-{N} starting at 1.
    # For single-file: resolve_single_output_name was already applied in the loop above.
    if len(processed) > 1:
        for seq, p in enumerate(processed, start=1):
            p.relative_path = resolve_batch_output_name(
                p.relative_path, naming_config, fmt.value, seq
            )
            p.filename = resolve_batch_output_name(
                p.filename, naming_config, fmt.value, seq
            )

    # ── Build response ────────────────────────────────────────────────────────
    if len(processed) == 1:
        return _build_single_response(processed[0], fmt)
    else:
        # Collect all errors (validation + transform)
        all_errors = batch_errors + transform_errors

        archived = [ArchivedFile(relative_path=p.relative_path, data=p.data) for p in processed]

        # First resolve final ZIP paths (including collision handling), then build manifest,
        # then write the ZIP with manifest.json included.
        _, resolved = zip_transformed_assets(archived)

        manifest_data = _build_manifest_payload(
            processed,
            [r.resolved_path for r in resolved],
            all_errors,
        )

        zip_bytes, _ = zip_transformed_assets(archived, manifest_entries=manifest_data)

        # Resolve ZIP filename — sanitize user stem or fall back to default
        resolved_zip_name = resolve_zip_name(naming_config.zip_name)

        return _build_zip_response(
            zip_bytes,
            len(processed),
            processed_original,
            processed_optimized,
            resolved_zip_name,
            error_count=len(all_errors),
        )
"""Asset Optimizer API — FastAPI application."""
from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
import os
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.schemas import ErrorCode, ErrorDetail, ErrorPayload
from app.services.archive import ArchivedFile, zip_transformed_assets
from app.services.transform import (
    OutputFormat,
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS,
    transform_image,
)


# ─── Constants ────────────────────────────────────────────────────────────────

MAX_FILES = 100
MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_PIXELS = 50 * 1024 * 1024  # 50 megapixels
PROCESSING_TIMEOUT_SECONDS = 120

DEFAULT_CORS_ORIGINS = (
    'http://localhost:5173',
    'http://127.0.0.1:5173',
)


# ─── Helpers ────────────────────────────────────────────────────────────────────

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

    import io
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
) -> Response:
    """Build a batch ZIP download response with summary headers."""
    headers = {
        "Content-Disposition": 'attachment; filename="optimized-assets.zip"',
        "Content-Type": "application/zip",
        "X-Asset-Processed-Count": str(processed_count),
        "X-Asset-Original-Bytes": str(original_bytes),
        "X-Asset-Optimized-Bytes": str(optimized_bytes),
    }
    return Response(content=zip_data, media_type="application/zip", headers=headers)


# ─── App lifecycle ─────────────────────────────────────────────────────────────

try:
    from pillow_avif import is_available as avif_available
    _avif_available = avif_available()
except ImportError:
    _avif_available = False

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Asset Optimizer API", version="0.2.0")

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
        'X-Asset-Original-Format',
        'X-Asset-Output-Format',
        'X-Asset-Original-Width',
        'X-Asset-Original-Height',
        'X-Asset-Output-Width',
        'X-Asset-Output-Height',
    ],
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {
        "message": "Asset Optimizer API is running",
        "service": "asset-optimizer-api",
        "status": "online",
    }


@app.get("/api/v1/formats")
async def list_formats() -> dict[str, list[str]]:
    return {
        "input_formats": list(SUPPORTED_INPUT_FORMATS),
        "output_formats": list(SUPPORTED_OUTPUT_FORMATS),
    }


@app.post("/api/v1/transform")
async def transform_assets(
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    quality: int = Form(...),
    max_width: int | None = Form(default=None),
    max_height: int | None = Form(default=None),
) -> Response:
    """
    Transform one or more images: resize, convert format, compress.
    Single file → direct download. Multiple files → ZIP.
    """
    # ── Parse and validate output format ─────────────────────────────────────
    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError:
        _raise_error(
            ErrorCode.UNSUPPORTED_OUTPUT_FORMAT,
            f"Output format '{output_format}' is not supported.",
            {"received": output_format, "supported": list(SUPPORTED_OUTPUT_FORMATS)},
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

    # ── Enforce hard limits ──────────────────────────────────────────────────
    total_bytes = _count_bytes(files)
    _check_limits(files, total_bytes)

    if not files:
        _raise_error(ErrorCode.FILE_COUNT_LIMIT, "No files provided.", {"max_files": MAX_FILES, "received": 0})

    # ── Read all file bytes ──────────────────────────────────────────────────
    file_data_pairs: list[tuple[UploadFile, bytes]] = []
    for f in files:
        data = await _read_upload_file(f)
        _validate_single_file(f, data)
        file_data_pairs.append((f, data))

    # ── Process files ────────────────────────────────────────────────────────
    start_time = time.monotonic()
    processed: list[ProcessedFile] = []
    total_original = 0
    total_optimized = 0

    for file, data in file_data_pairs:
        elapsed = time.monotonic() - start_time
        if elapsed > PROCESSING_TIMEOUT_SECONDS:
            _raise_error(
                ErrorCode.PROCESSING_TIMEOUT,
                "Processing timed out. Try fewer or smaller files.",
                {"timeout_seconds": PROCESSING_TIMEOUT_SECONDS},
            )

        source_relative_path = getattr(file, "webkitRelativePath", "") or file.filename or "unknown"
        source_filename = file.filename or "unknown"
        relative_path = _replace_extension(source_relative_path, fmt)
        filename = _replace_extension(source_filename, fmt)

        try:
            transformed_data, metadata = transform_image(
                data=data,
                output_format=fmt,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
            )
        except Exception as e:
            _raise_error(
                ErrorCode.INVALID_IMAGE,
                f"Failed to transform '{filename}': {e}",
                {"filename": source_filename},
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
        total_original += metadata.original_bytes
        total_optimized += metadata.optimized_bytes

    # ── Build response ───────────────────────────────────────────────────────
    if len(processed) == 1:
        return _build_single_response(processed[0], fmt)
    else:
        archived = [ArchivedFile(relative_path=p.relative_path, data=p.data) for p in processed]
        zip_data = zip_transformed_assets(archived)
        return _build_zip_response(zip_data, len(processed), total_original, total_optimized)

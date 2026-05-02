"""Path resolution and validation for folder/batch uploads.

Canonical payload: ordered array of relative paths in the same order as ``files``.
Legacy payload: filename → path object (accepted for backward-compat draft clients).
"""
from __future__ import annotations

import json
import os
import posixpath
from typing import Any

from fastapi import HTTPException

from app.schemas import ErrorCode, ErrorDetail, ErrorPayload


def _raise_invalid(message: str, details: dict[str, Any] | None = None) -> None:
    raise HTTPException(
        status_code=422,
        detail=ErrorPayload(
            error=ErrorDetail(code=ErrorCode.INVALID_PATHS_FORMAT, message=message, details=details)
        ).model_dump(mode="json"),
    )


def _normalize_path_segments(path: str) -> list[str]:
    """Split on /, strip empty and bare dot segments, return parts."""
    return [seg for seg in path.replace("\\", "/").split("/") if seg and seg != "."]


def _sanitize_path(path: str) -> str:
    """Normalize path: strip . segments, collapse /, convert \\ to /, strip leading ./."""
    parts = _normalize_path_segments(path)
    normalized = posixpath.join(*parts) if parts else ""
    # Strip leading ./ that Join can leave
    normalized = normalized.lstrip("./")
    return normalized


def _rebuild_with_uploaded_filename(path: str, filename: str) -> str:
    """Use only the directory structure from the provided path and append the actual uploaded filename."""
    clean = _sanitize_path(path)
    directory = posixpath.dirname(clean)

    if not directory or directory == ".":
        return filename

    return posixpath.join(directory, filename)


def resolve_upload_paths(
    files: list[Any],
    paths_raw: str | None,
) -> list[str] | None:
    """Resolve sanitized relative paths from the optional ``paths`` multipart field.

    Canonical payload: JSON array of relative paths, same order as ``files``.
    Legacy payload: JSON object mapping filename → path (backward compat).

    Returns:
        List of sanitized relative paths, one per file, in the same order as ``files``.
        ``None`` when ``paths_raw`` is absent (backward-compat fallback to flat ZIP).

    Raises HTTPException(422) with ``INVALID_PATHS_FORMAT`` for:
        - Malformed JSON
        - Absolute paths, drive prefixes, or ``..`` traversal
        - Array length mismatch vs file count

    Notes:
        - Directory structure comes from the provided path metadata.
        - The final basename always comes from the actual uploaded file name.
        - This avoids false mismatches while keeping the ordered-array contract safe.
    """
    if paths_raw is None or paths_raw == "":
        return None

    try:
        parsed = json.loads(paths_raw)
    except json.JSONDecodeError:
        _raise_invalid("paths field must be valid JSON", {"received": paths_raw[:200]})

    # Determine payload shape: canonical array vs legacy object
    if isinstance(parsed, list):
        raw_paths: list[str] = parsed
    elif isinstance(parsed, dict):
        # Legacy object: filename → path. Build ordered list preserving files order.
        raw_paths = [parsed.get(f.filename, f.filename) for f in files]
    else:
        _raise_invalid(
            "paths field must be a JSON array or a JSON object",
            {"received_type": type(parsed).__name__},
        )

    if len(raw_paths) != len(files):
        _raise_invalid(
            f"paths array length ({len(raw_paths)}) must match file count ({len(files)})",
            {"paths_count": len(raw_paths), "file_count": len(files)},
        )

    sanitized: list[str] = []
    for file, raw_path in zip(files, raw_paths):
        if not isinstance(raw_path, str):
            _raise_invalid("each path in the array must be a string", {"received_type": type(raw_path).__name__})

        # Reject absolute paths
        if posixpath.isabs(raw_path):
            _raise_invalid("absolute paths are not allowed", {"path": raw_path})

        # Reject drive prefixes (e.g. C:, /c/, etc.)
        if len(raw_path) >= 2 and raw_path[1] == ":":
            _raise_invalid("drive prefixes are not allowed", {"path": raw_path})

        # Reject .. traversal
        parts = _normalize_path_segments(raw_path)
        if ".." in parts:
            _raise_invalid("'..' path traversal is not allowed", {"path": raw_path})

        sanitized.append(_rebuild_with_uploaded_filename(raw_path, file.filename))

    return sanitized

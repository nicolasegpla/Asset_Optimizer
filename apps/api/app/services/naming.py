"""Naming service: sanitization, config validation, and output filename rewriting."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.schemas import ErrorCode

# Characters disallowed by the sanitization spec
_DISALLOWED_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Max length for any naming field after sanitization
_MAX_NAME_LENGTH = 128

# Default ZIP stem when none provided
_DEFAULT_ZIP_STEM = "optimized-assets"

# Default output stem for batch sequential naming
_DEFAULT_OUTPUT_STEM = "file"


def _sanitize_field(value: str | None) -> str:
    """
    Sanitize a single naming field.

    Rules:
    - Remove disallowed chars (< > : " / \ | ? * and control chars)
    - Trim leading/trailing whitespace and dots
    - Collapse internal runs of spaces to a single space
    - Strip extension if user somehow included one (we only keep the stem)

    Returns the sanitized string.
    Raises ValueError if the result is empty or exceeds MAX_NAME_LENGTH.
    """
    if value is None:
        return ""

    # Remove disallowed characters
    sanitized = _DISALLOWED_CHARS.sub("", value)

    # Remove control characters that slipped through
    sanitized = "".join(char for char in sanitized if ord(char) >= 0x20)

    # Trim leading/trailing whitespace and dots
    sanitized = sanitized.strip(" \t\r\n.")
    sanitized = sanitized.strip()

    # Collapse internal runs of spaces
    sanitized = re.sub(r" {2,}", " ", sanitized)

    if not sanitized:
        raise ValueError("Field became empty after sanitization.")

    if len(sanitized) > _MAX_NAME_LENGTH:
        raise ValueError(
            f"Field exceeds maximum length of {_MAX_NAME_LENGTH} characters."
        )

    return sanitized


def _strip_extension(stem: str) -> str:
    """Strip any existing extension from a filename stem."""
    return stem.rsplit(".", maxsplit=1)[0]


def _normalize_ext(output_format: str) -> str:
    """Return the file extension for a given output format."""
    return ".jpeg" if output_format == "jpg" else f".{output_format}"


@dataclass(frozen=True)
class NamingConfig:
    """Validated naming configuration from the request form fields."""

    zip_name: str | None  # None means use default
    output_prefix: str | None  # single-file only
    output_suffix: str | None  # single-file only
    output_stem: str | None  # batch/folder only; None means default "file"


def sanitize_naming_config(
    zip_name: str | None,
    output_prefix: str | None,
    output_suffix: str | None,
    output_stem: str | None,
) -> NamingConfig:
    """
    Validate and sanitize all naming form fields.

    Empty-after-sanitize or too-long fields raise ValueError,
    converted to a 422 INVALID_NAMING_CONFIG error by the caller.
    """
    sanitized_zip = _sanitize_field(zip_name) if zip_name else None
    sanitized_prefix = _sanitize_field(output_prefix) if output_prefix else None
    sanitized_suffix = _sanitize_field(output_suffix) if output_suffix else None
    sanitized_stem = _sanitize_field(output_stem) if output_stem else None

    return NamingConfig(
        zip_name=sanitized_zip,
        output_prefix=sanitized_prefix,
        output_suffix=sanitized_suffix,
        output_stem=sanitized_stem,
    )


def resolve_zip_name(zip_name: str | None) -> str:
    """
    Resolve the final ZIP filename stem.

    - If zip_name is None → return default stem ("optimized-assets")
    - Sanitize the provided stem, strip any extension, append ".zip"

    Returns e.g. "my-assets.zip".
    Raises ValueError on empty-after-sanitize.
    """
    if zip_name is None:
        return f"{_DEFAULT_ZIP_STEM}.zip"

    sanitized = _sanitize_field(zip_name)
    stem = _strip_extension(sanitized)
    return f"{stem}.zip"


def resolve_single_output_name(
    filename: str,
    config: NamingConfig,
    output_format: str,
) -> str:
    """
    Resolve output filename for a SINGLE-FILE download.

    Rules:
    - Original basename is PRESERVED (only extension may change)
    - output_prefix inserts before the stem
    - output_suffix inserts before the extension
    - NO sequential numbering for single-file
    - output_stem is IGNORED for single-file

    Directory components are preserved; only the basename stem is modified.
    """
    dirname, basename = os.path.split(filename)
    stem, _ = os.path.splitext(basename)

    if config.output_prefix:
        stem = f"{config.output_prefix}{stem}"

    if config.output_suffix:
        stem = f"{stem}{config.output_suffix}"

    final_ext = _normalize_ext(output_format)
    final_name = f"{stem}{final_ext}"

    if dirname:
        return f"{dirname}/{final_name}"
    return final_name


def resolve_batch_output_name(
    filename: str,
    config: NamingConfig,
    output_format: str,
    sequence_number: int,
) -> str:
    """
    Resolve output filename for a BATCH/FOLDER download.

    Rules:
    - Original basename is REPLACED entirely with {stem}-{N}
    - output_stem defaults to "file" if not provided
    - output_prefix and output_suffix are IGNORED for batch
    - sequence_number starts at 1 (caller is responsible for this)
    - Directory structure is PRESERVED; only the basename is replaced

    The sequence_number is the N in {stem}-{N}.{ext}.
    """
    dirname, basename = os.path.split(filename)
    # Extract the directory path; stem is discarded and replaced
    _ = basename  # original basename is not used

    stem = config.output_stem if config.output_stem else _DEFAULT_OUTPUT_STEM
    final_ext = _normalize_ext(output_format)
    final_name = f"{stem}-{sequence_number}{final_ext}"

    if dirname:
        return f"{dirname}/{final_name}"
    return final_name

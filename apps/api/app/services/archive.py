"""ZIP archive creation preserving relative paths."""
from __future__ import annotations

import io
import json
import os
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import NamedTuple


class ArchivedFile(NamedTuple):
    relative_path: str
    data: bytes


@dataclass
class ResolvedPath:
    """A file's resolved ZIP path after collision handling."""
    original_path: str
    resolved_path: str  # what actually went into the ZIP


def zip_transformed_assets(
    files: list[ArchivedFile],
    manifest_entries: list[dict] | None = None,
) -> tuple[bytes, list[ResolvedPath]]:
    """
    Create a ZIP archive from a list of (relative_path, bytes) tuples.

    Preserves webkitRelativePath folder structure.
    Handles filename collisions by appending -1, -2 suffixes.

    Returns (zip_bytes, resolved_paths) where resolved_paths[i].resolved_path
    is the actual ZIP entry name for files[i], accounting for collisions.
    """
    buffer = io.BytesIO()

    resolved_paths: list[ResolvedPath] = []

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Detect collisions by normalized path
        counter: Counter[str] = Counter()
        seen: dict[str, int] = {}

        for file in files:
            original_path = file.relative_path
            normalized = original_path.replace("\\", "/")

            # Track duplicates
            counter[normalized] += 1

            # Handle collision: append -1, -2, etc.
            if counter[normalized] > 1:
                seen[normalized] = seen.get(normalized, 1)
                collision_count = seen[normalized]
                seen[normalized] = collision_count + 1

                name, ext = os.path.splitext(normalized)
                # e.g. "image.png" → "image-2.png", "image-3.png"
                normalized = f"{name}-{collision_count}{ext}"

            # Normalize to forward slashes for ZIP
            zip_path = normalized.replace("\\", "/")

            resolved_paths.append(ResolvedPath(original_path=original_path, resolved_path=zip_path))

            zf.writestr(zip_path, file.data)

        # Write manifest.json if entries provided
        if manifest_entries is not None:
            manifest_json = json.dumps(manifest_entries, indent=2)
            zf.writestr("manifest.json", manifest_json.encode("utf-8"))

    buffer.seek(0)
    return buffer.getvalue(), resolved_paths

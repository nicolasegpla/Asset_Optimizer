"""ZIP archive creation preserving relative paths."""
from __future__ import annotations

import io
import os
import zipfile
from collections import Counter
from typing import NamedTuple


class ArchivedFile(NamedTuple):
    relative_path: str
    data: bytes


def zip_transformed_assets(files: list[ArchivedFile]) -> bytes:
    """
    Create a ZIP archive from a list of (relative_path, bytes) tuples.

    Preserves webkitRelativePath folder structure.
    Handles filename collisions by appending -1, -2 suffixes.
    """
    buffer = io.BytesIO()

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

            zf.writestr(zip_path, file.data)

    buffer.seek(0)
    return buffer.getvalue()

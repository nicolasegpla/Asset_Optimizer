"""Pure GLB optimization functions — no FastAPI imports."""
from __future__ import annotations

import asyncio
import logging
import os
import struct
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GLB_MAGIC = b"glTF"

# Subprocess timeout for gltf-transform (seconds)
GLB_OPTIMIZATION_TIMEOUT = 120


@dataclass(frozen=True)
class GlbOptimizationMetadata:
    original_bytes: int
    optimized_bytes: int
    compression_ratio: float


def validate_glb_magic(data: bytes) -> None:
    """Raise ValueError if data does not start with 'glTF' magic (offset 0)."""
    if len(data) < 4:
        raise ValueError("File too short to be a valid GLB.")
    if data[:4] != GLB_MAGIC:
        raise ValueError("Invalid GLB file: missing 'glTF' magic bytes.")


async def optimize_glb(data: bytes) -> tuple[bytes, GlbOptimizationMetadata]:
    """
    Run gltf-transform optimize via async subprocess.

    Uses temporary files for input/output, applies draco compression.
    (gltf-transform optimize handles dedup/prune/quantize by default.)
    Returns optimized bytes and metadata.
    """
    original_bytes = len(data)

    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as infile:
        infile.write(data)
        input_path = infile.name

    output_path = input_path.replace(".glb", ".optimized.glb")

    try:
        # gltf-transform v4+ optimize does dedup/prune/quantize by default
        cmd = [
            "gltf-transform",
            "optimize",
            input_path,
            output_path,
            "--compress",
            "draco",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=GLB_OPTIMIZATION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError("GLB optimization timed out after 120 seconds.")

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace")[:500] if stderr else "Unknown error"
            raise RuntimeError(f"GLB optimization failed: {err_msg}")

        if not os.path.exists(output_path):
            raise RuntimeError("GLB optimization did not produce output file.")

        with open(output_path, "rb") as f:
            optimized_data = f.read()

        optimized_bytes = len(optimized_data)
        compression_ratio = (
            round((1 - optimized_bytes / original_bytes) * 100, 2)
            if original_bytes > 0
            else 0.0
        )

        metadata = GlbOptimizationMetadata(
            original_bytes=original_bytes,
            optimized_bytes=optimized_bytes,
            compression_ratio=compression_ratio,
        )

        return optimized_data, metadata

    finally:
        for path in (input_path, output_path):
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass

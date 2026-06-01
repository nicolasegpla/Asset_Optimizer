"""Test fixtures for asset-optimizer API tests."""
from __future__ import annotations

import io
import json
import os
import struct
from pathlib import Path

import pytest
from PIL import Image

# Project root for fixture images
FIXTURE_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_jpg_bytes() -> bytes:
    """Generate a small valid JPG image in memory."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Generate a small valid PNG image in memory."""
    img = Image.new("RGBA", (100, 100), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def sample_webp_bytes() -> bytes:
    """Generate a small valid WEBP image in memory."""
    img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def sample_rgba_png_bytes() -> bytes:
    """Generate an RGBA PNG (with transparency) for RGBA→RGB JPG tests."""
    img = Image.new("RGBA", (50, 50), color=(100, 50, 200, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def large_dimensions_bytes() -> bytes:
    """Generate an image that exceeds MAX_PIXELS (50 MP)."""
    # 10000 x 10000 = 100 MP > 50 MP limit
    img = Image.new("RGB", (10000, 10000), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def corrupt_bytes() -> bytes:
    """Return bytes that are not a valid image."""
    return b"This is not an image file at all"


def _make_minimal_glb() -> bytes:
    """Create a minimal valid GLB file for testing."""
    import json
    import struct

    gltf_json = json.dumps({
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": []
    }).encode("utf-8")

    # Pad JSON to 4-byte boundary
    json_padding = (4 - (len(gltf_json) % 4)) % 4
    gltf_json += b" " * json_padding

    json_chunk_len = len(gltf_json)
    json_chunk_type = 0x4E4F534A  # "JSON"

    # Header
    magic = b"glTF"
    version = struct.pack("<I", 2)
    length = struct.pack("<I", 12 + 8 + json_chunk_len)

    # JSON chunk header
    json_chunk = struct.pack("<I", json_chunk_len) + struct.pack("<I", json_chunk_type) + gltf_json

    return magic + version + length + json_chunk


@pytest.fixture
def sample_glb_bytes() -> bytes:
    """Generate a small valid GLB file in memory."""
    return _make_minimal_glb()


@pytest.fixture
def oversized_glb_bytes() -> bytes:
    """Generate a GLB file that exceeds MAX_GLB_PER_FILE (100 MB)."""
    # Start with valid GLB header, then pad to > 100 MB
    base = _make_minimal_glb()
    target_size = (100 * 1024 * 1024) + 1024  # 100 MB + 1 KB
    padding_needed = target_size - len(base)
    if padding_needed > 0:
        # Add a BIN chunk with padding
        bin_data = b"\x00" * padding_needed
        # Pad to 4-byte boundary
        bin_padding = (4 - (len(bin_data) % 4)) % 4
        bin_data += b"\x00" * bin_padding
        bin_chunk_len = len(bin_data)
        bin_chunk_type = 0x004E4942  # "BIN\0"
        bin_chunk = struct.pack("<I", bin_chunk_len) + struct.pack("<I", bin_chunk_type) + bin_data

        # Update total length
        total_length = 12 + 8 + len(base) - 12 + 8 + len(bin_data)
        # Rebuild with corrected length
        magic = base[:4]
        version = base[4:8]
        length = struct.pack("<I", total_length)
        return magic + version + length + base[12:] + bin_chunk
    return base
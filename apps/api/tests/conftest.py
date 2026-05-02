"""Test fixtures for asset-optimizer API tests."""
from __future__ import annotations

import io
import os
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
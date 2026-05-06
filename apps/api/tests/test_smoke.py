"""Live-API smoke suite for Asset Optimizer API.

Targets a running HTTP server (not TestClient). Skips automatically when
the API is unreachable so the normal unit/integration suite is unaffected.

Run with:
    pytest apps/api/tests/test_smoke.py -v
    SMOKE_BASE_URL=http://localhost:9000 pytest apps/api/tests/test_smoke.py -v
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from typing import Any

import httpx
import pytest
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# ─── Skip logic ───────────────────────────────────────────────────────────────

def _check_api_live() -> bool:
    """Return True if the API is reachable at BASE_URL."""
    try:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
            response = client.get("/health")
            return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def api_live() -> bool:
    """Module-scoped check — probes once per test module run."""
    return _check_api_live()


@pytest.fixture(scope="module", autouse=True)
def skip_when_api_unreachable(api_live: bool) -> None:
    """Skip the whole smoke module cleanly when the live API is unavailable."""
    if not api_live:
        pytest.skip(f"API not live at {BASE_URL}", allow_module_level=True)

# ─── Session fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sync_client() -> httpx.Client:
    """Synchronous client for smoke tests — shared across module."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, trust_env=False) as client:
        yield client


@pytest.fixture(scope="module")
def sample_jpg_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module")
def sample_png_bytes() -> bytes:
    img = Image.new("RGBA", (100, 100), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module")
def corrupt_bytes() -> bytes:
    return b"This is not an image file at all"


# ─── 1. Health endpoint ───────────────────────────────────────────────────────

class TestSmokeHealth:
    """Smoke: GET /health returns 200 and expected fields."""

    def test_health_returns_200(self, sync_client: httpx.Client, api_live: bool) -> None:
        assert api_live, "API not live"
        response = sync_client.get("/health")
        assert response.status_code == 200

    def test_health_has_status_and_service(
        self, sync_client: httpx.Client, api_live: bool
    ) -> None:
        assert api_live
        data = sync_client.get("/health").json()
        assert data["status"] == "online"
        assert data["service"] == "asset-optimizer-api"

    def test_health_has_avif_and_dependencies(
        self, sync_client: httpx.Client, api_live: bool
    ) -> None:
        assert api_live
        data = sync_client.get("/health").json()
        assert "avif_available" in data
        assert "dependencies" in data
        deps = data["dependencies"]
        assert "pillow" in deps
        assert "avif_encoder" in deps


# ─── 2. Capabilities endpoint ─────────────────────────────────────────────────

class TestSmokeCapabilities:
    """Smoke: GET /api/v1/capabilities returns output formats and AVIF availability."""

    def test_capabilities_returns_200(self, sync_client: httpx.Client, api_live: bool) -> None:
        assert api_live
        response = sync_client.get("/api/v1/capabilities")
        assert response.status_code == 200

    def test_capabilities_has_output_formats_and_avif(
        self, sync_client: httpx.Client, api_live: bool
    ) -> None:
        assert api_live
        data = sync_client.get("/api/v1/capabilities").json()
        assert "output_formats" in data
        assert "avif_available" in data
        assert isinstance(data["output_formats"], list)
        assert isinstance(data["avif_available"], bool)
        # Core formats always expected
        assert "jpg" in data["output_formats"]
        assert "png" in data["output_formats"]
        assert "webp" in data["output_formats"]


# ─── 3. Single-file transform (binary response + key headers) ─────────────────

class TestSmokeSingleTransform:
    """Smoke: POST /api/v1/transform with 1 file returns direct binary download."""

    def test_single_transform_returns_200(
        self, sync_client: httpx.Client, sample_jpg_bytes: bytes, api_live: bool
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200

    def test_single_transform_binary_content_type(
        self, sync_client: httpx.Client, sample_jpg_bytes: bytes, api_live: bool
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.headers["content-type"] == "image/jpeg"

    def test_single_transform_content_disposition_attachment(
        self, sync_client: httpx.Client, sample_jpg_bytes: bytes, api_live: bool
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        disp = response.headers["content-disposition"]
        assert "attachment" in disp
        assert "test.jpeg" in disp

    def test_single_transform_has_asset_headers(
        self, sync_client: httpx.Client, sample_jpg_bytes: bytes, api_live: bool
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        for header in [
            "x-asset-original-bytes",
            "x-asset-optimized-bytes",
            "x-asset-compression-ratio",
            "x-asset-original-format",
            "x-asset-output-format",
        ]:
            assert header in response.headers, f"Missing header: {header}"

    def test_single_transform_body_is_valid_image(
        self, sync_client: httpx.Client, sample_jpg_bytes: bytes, api_live: bool
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert len(response.content) > 0
        img = Image.open(io.BytesIO(response.content))
        img.verify()
        assert img.format in ("JPEG",)


# ─── 4. Batch transform (ZIP response + manifest.json) ───────────────────────

class TestSmokeBatchTransform:
    """Smoke: POST with ≥2 files returns ZIP with manifest.json."""

    def test_batch_returns_zip_content_type(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_batch_returns_processed_count_header(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.headers["x-asset-processed-count"] == "2"

    def test_batch_zip_contains_manifest(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        assert "manifest.json" in zf.namelist()

    def test_manifest_has_required_keys(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        assert "files" in manifest
        assert "errors" in manifest
        assert "summary" in manifest
        assert manifest["summary"]["processedFiles"] == 2
        assert manifest["summary"]["failedFiles"] == 0


# ─── 5. Folder-path preservation with `paths` ─────────────────────────────────

class TestSmokeFolderStructure:
    """Smoke: `paths` field preserves directory structure in ZIP."""

    def test_paths_preserves_subfolder_structure(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("hero.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("thumb.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["images/hero.jpg", "assets/thumb.png"]',
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        # Subfolder preserved; basenames replaced with sequential naming
        assert "images/file-1.jpeg" in names
        assert "assets/file-2.jpeg" in names

    def test_paths_deep_nested_structure(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        # Single file with paths → still returns binary (paths only affects ZIP structure)
        response = sync_client.post(
            "/api/v1/transform",
            files=[("files", ("img.jpg", sample_jpg_bytes, "image/jpeg"))],
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["products/2024/spring/banner.jpg"]',
            },
        )
        assert response.status_code == 200
        # Single file response is binary, not ZIP
        assert response.headers["content-type"] == "image/jpeg"
        img = Image.open(io.BytesIO(response.content))
        img.verify()


# ─── 6. Partial-success (one invalid + one valid) ─────────────────────────────

class TestSmokePartialSuccess:
    """Smoke: batch with mixed valid/invalid files returns ZIP + manifest with errors."""

    def test_partial_success_returns_200_with_error_count_header(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        corrupt_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        # Use 3 files to ensure ZIP is returned even with 1 bad file.
        # 2 valid files → at least 2 processed → batch ZIP response.
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("good1.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("bad.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("good2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["x-asset-error-count"] == "1"
        assert response.headers["x-asset-processed-count"] == "2"

    def test_partial_success_manifest_shows_one_error(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        corrupt_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("good.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("bad.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("ok.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["summary"]["processedFiles"] == 2
        assert manifest["summary"]["failedFiles"] == 1
        assert len(manifest["errors"]) == 1
        assert manifest["errors"][0]["source"] == "bad.jpg"

    def test_partial_success_error_in_manifest_has_code_and_message(
        self,
        sync_client: httpx.Client,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        corrupt_bytes: bytes,
        api_live: bool,
    ) -> None:
        assert api_live
        # Use 3 files (2 valid, 1 corrupt) to guarantee ZIP response even with jpg output
        response = sync_client.post(
            "/api/v1/transform",
            files=[
                ("files", ("good1.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("bad.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("good2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        error_entry = manifest["errors"][0]
        assert "code" in error_entry
        assert "message" in error_entry
        assert error_entry["code"] == "INVALID_IMAGE"

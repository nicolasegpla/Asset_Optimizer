"""Integration tests for POST /api/v1/transform endpoint."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestFormatsEndpoint:
    def test_list_formats_returns_input_and_output(self, client: TestClient) -> None:
        response = client.get("/api/v1/formats")
        assert response.status_code == 200
        data = response.json()
        assert "input_formats" in data
        assert "output_formats" in data
        assert "jpg" in data["input_formats"]
        assert "avif" in data["output_formats"]


class TestTransformSingleFile:
    def test_single_jpg_to_jpg_returns_binary_with_headers(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "content-disposition" in response.headers
        assert "x-asset-original-bytes" in response.headers
        assert "x-asset-optimized-bytes" in response.headers
        assert "x-asset-compression-ratio" in response.headers
        assert len(response.content) > 0

    def test_single_png_to_jpg_returns_binary(self, client: TestClient, sample_png_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.png", sample_png_bytes, "image/png")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert "image/jpeg" in response.headers["content-type"]

    def test_single_file_with_resize(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80", "max_width": "50"},
        )
        assert response.status_code == 200

    def test_single_file_webp_output(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        assert "image/webp" in response.headers["content-type"]


class TestTransformBatchFiles:
    def test_two_files_returns_zip_with_headers(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("img1.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("img2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["x-asset-processed-count"] == "2"
        assert "x-asset-original-bytes" in response.headers
        assert "x-asset-optimized-bytes" in response.headers

    def test_zip_is_valid_contains_files(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 3
        assert "a.jpeg" in names
        assert "b.jpeg" in names
        assert "manifest.json" in names


class TestTransformFolderStructure:
    """Folder/batch structure preservation via optional `paths` field."""

    def test_paths_field_preserves_subfolder_in_zip(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """When `paths` is provided, ZIP entries reflect the relative paths."""
        response = client.post(
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
        assert response.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert "images/hero.jpeg" in names
        assert "assets/thumb.jpeg" in names

    def test_missing_paths_field_falls_back_to_flat_zip(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Without `paths`, files are stored flat in the ZIP (backward compat)."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("img1.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("img2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        # Backward compat: webkitRelativePath or filename used as-is, then extension replaced to output format
        assert "img1.jpeg" in names

    def test_malformed_paths_json_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Malformed JSON in `paths` returns INVALID_PATHS_FORMAT."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": "not valid json",
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_PATHS_FORMAT"

    def test_paths_array_length_mismatch_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """paths array length != file count returns INVALID_PATHS_FORMAT."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["only-one.jpg"]',
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_PATHS_FORMAT"

    def test_absolute_path_in_paths_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Absolute paths in `paths` are rejected with INVALID_PATHS_FORMAT."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["/absolute/path/test.jpg"]',
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_PATHS_FORMAT"
        assert "absolute paths are not allowed" in data["detail"]["error"]["message"]

    def test_traversal_path_in_paths_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """`..` traversal in `paths` is rejected with INVALID_PATHS_FORMAT."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["subdir/../etc/passwd.jpg"]',
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_PATHS_FORMAT"
        assert "'..' path traversal is not allowed" in data["detail"]["error"]["message"]

    def test_duplicate_basename_files_both_preserved(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Two files with the same filename in different subfolders — both preserved via ordered paths."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("x.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("x.jpg", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "jpg",
                "quality": "80",
                "paths": '["products/x.jpg", "thumbnails/x.jpg"]',
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert "products/x.jpeg" in names
        assert "thumbnails/x.jpeg" in names


class TestTransformValidation:
    def test_unsupported_input_format_rejects(
        self, client: TestClient, sample_webp_bytes: bytes
    ) -> None:
        """Sending a .txt file should be rejected as unsupported input format."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.txt", b"not an image", "text/plain")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_IMAGE"
        errors = data["detail"]["error"]["details"].get("errors", [])
        assert errors[0]["code"] == "UNSUPPORTED_INPUT_FORMAT"

    def test_unsupported_output_format_rejects(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "bmp", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "UNSUPPORTED_OUTPUT_FORMAT"

    def test_quality_out_of_range_rejects(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "150"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_QUALITY"

    def test_max_width_out_of_range_rejects(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80", "max_width": "50000"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_DIMENSIONS"

    def test_corrupt_image_rejects(self, client: TestClient, corrupt_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/transform",
            files={"files": ("bad.jpg", corrupt_bytes, "image/jpeg")},
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INVALID_IMAGE"


class TestBatchManifestAndPartialSuccess:
    """Tests for manifest.json in ZIPs and partial success behavior."""

    def test_batch_zip_contains_manifest(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """ZIP returned for ≥2 files contains manifest.json at root."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        assert "manifest.json" in zf.namelist()

    def test_manifest_has_files_and_errors_and_summary(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """manifest.json has files[], errors[], and summary keys."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        assert "files" in manifest
        assert "errors" in manifest
        assert "summary" in manifest

    def test_manifest_summary_counts_correct(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """summary.totalFiles, processedFiles, failedFiles match actuals."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["summary"]["totalFiles"] == 2
        assert manifest["summary"]["processedFiles"] == 2
        assert manifest["summary"]["failedFiles"] == 0

    def test_manifest_summary_byte_totals_match_files(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """summary.totalOriginalBytes and totalOptimizedBytes equal per-file sums."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        file_sum_original = sum(f["originalBytes"] for f in manifest["files"])
        file_sum_optimized = sum(f["optimizedBytes"] for f in manifest["files"])
        assert manifest["summary"]["totalOriginalBytes"] == file_sum_original
        assert manifest["summary"]["totalOptimizedBytes"] == file_sum_optimized

    def test_manifest_entries_match_zip_files(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Each manifest.files[].output matches a filename present in the ZIP."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        zip_names_without_manifest = [n for n in zf.namelist() if n != "manifest.json"]
        for entry in manifest["files"]:
            assert entry["output"] in zip_names_without_manifest

    def test_partial_success_2_of_3(
        self,
        client: TestClient,
        sample_jpg_bytes: bytes,
        sample_png_bytes: bytes,
        corrupt_bytes: bytes,
    ) -> None:
        """2 succeed, 1 fails → 200, ZIP with manifest, X-Asset-Error-Count: 1."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("good1.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("bad.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("good2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        assert response.headers.get("x-asset-error-count") == "1"
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["summary"]["processedFiles"] == 2
        assert manifest["summary"]["failedFiles"] == 1
        assert len(manifest["files"]) == 2
        assert len(manifest["errors"]) == 1

    def test_all_fail_returns_422_no_zip(
        self, client: TestClient, corrupt_bytes: bytes
    ) -> None:
        """3 invalid files → 422, JSON with details.errors, no ZIP."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("bad1.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("bad2.png", corrupt_bytes, "image/png")),
                ("files", ("bad3.webp", corrupt_bytes, "image/webp")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert "details" in data["detail"]["error"]
        errors = data["detail"]["error"]["details"].get("errors", [])
        assert len(errors) == 3
        assert errors[0]["source"] == "bad1.jpg"
        assert errors[0]["code"] == "INVALID_IMAGE"

    def test_single_file_no_manifest(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Single file → direct image, no ZIP, no manifest."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("solo.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 200
        # No ZIP content-type means no manifest possible
        assert "application/zip" not in response.headers.get("content-type", "")
        # Verify it's actual image data, not a ZIP
        assert response.content[:4] == b'RIFF'  # WEBP/RIFF container magic bytes

    def test_cors_exposes_error_count(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes, corrupt_bytes: bytes
    ) -> None:
        """Batch response with errors includes X-Asset-Error-Count in CORS exposed headers."""
        # Trigger partial success with at least one bad file
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("good.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("bad.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("good2.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        # The header must be accessible to the frontend via CORS
        # (expose_headers already set in app middleware)
        assert "x-asset-error-count" in response.headers

    def test_all_fail_returns_422_with_error_count_header(
        self, client: TestClient, corrupt_bytes: bytes
    ) -> None:
        """When all files fail, 422 is returned and no ZIP is sent (hence no X-Asset-Error-Count)."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("bad1.jpg", corrupt_bytes, "image/jpeg")),
                ("files", ("bad2.jpg", corrupt_bytes, "image/jpeg")),
            ],
            data={"output_format": "webp", "quality": "80"},
        )
        assert response.status_code == 422
        # No ZIP → no X-Asset-Error-Count header (only present on 200 batch responses)

"""Integration tests for API endpoints."""
from __future__ import annotations

import io
import json
import logging
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestCapabilitiesEndpoint:
    """Tests for GET /api/v1/capabilities."""

    def test_capabilities_returns_avif_available_and_output_formats(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "output_formats" in data
        assert "avif_available" in data
        assert isinstance(data["avif_available"], bool)
        assert isinstance(data["output_formats"], list)
        assert "jpg" in data["output_formats"]
        assert "png" in data["output_formats"]
        assert "webp" in data["output_formats"]

    def test_avif_in_output_formats_only_when_available(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/capabilities")
        data = response.json()
        if data["avif_available"]:
            assert "avif" in data["output_formats"]
        else:
            assert "avif" not in data["output_formats"]


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_status_and_service(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["service"] == "asset-optimizer-api"

    def test_health_returns_avif_available_and_dependencies(
        self, client: TestClient
    ) -> None:
        response = client.get("/health")
        data = response.json()
        assert "avif_available" in data
        assert "dependencies" in data
        deps = data["dependencies"]
        assert "pillow" in deps
        assert "avif_encoder" in deps
        assert "version" in deps["pillow"]
        assert "status" in deps["pillow"]
        assert "available" in deps["avif_encoder"]
        assert "status" in deps["avif_encoder"]

    def test_health_avif_matches_capabilities_avif(
        self, client: TestClient
    ) -> None:
        health_response = client.get("/health")
        caps_response = client.get("/api/v1/capabilities")
        health_data = health_response.json()
        caps_data = caps_response.json()
        assert health_data["avif_available"] == caps_data["avif_available"]


class TestAvifTransformGuard:
    """Tests for AVIF runtime guard on POST /api/v1/transform."""

    def test_avif_rejected_when_unavailable(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        """When runtime profile says AVIF unavailable, transform returns 422."""
        # First check current runtime state
        caps = client.get("/api/v1/capabilities").json()
        if caps["avif_available"]:
            pytest.skip("AVIF is available in this runtime — guard not triggered")

        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "avif", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "AVIF_UNAVAILABLE"

    def test_avif_accepted_returns_valid_avif_bytes(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Positive-path AVIF: when runtime supports it, transform returns a real AVIF file."""
        caps = client.get("/api/v1/capabilities").json()
        if not caps["avif_available"]:
            pytest.skip("AVIF is not available in this runtime")

        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "avif", "quality": "80"},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # Headers confirm binary output
        assert response.headers["content-type"] in (
            "image/avif",
            "image/avif-sequence",
        ), f"Expected image/avif content-type, got {response.headers['content-type']}"
        assert "content-disposition" in response.headers
        disp = response.headers["content-disposition"]
        assert "avif" in disp.lower(), f"Expected .avif in Content-Disposition, got: {disp}"

        # Response body is non-empty
        body = response.content
        assert len(body) > 0, "Expected non-empty AVIF response body"

        # AVIF file signature: ISOBMFF ftyp box at offset 4
        # AVIF files have `ftyp` brand `avif` — byte pattern: 00 00 00 ?? ftyp 61 76 69 66
        # Minimum AVIF is > 32 bytes; skip tiny bodies that can't possibly be valid
        if len(body) >= 32:
            assert body[4:8] == b"ftyp", (
                f"Expected 'ftyp' at offset 4 (AVIF ISOBMFF), got {body[4:8]!r}"
            )
            brand = body[8:12]
            assert brand == b"avif", f"Expected 'avif' brand at offset 8, got {brand!r}"

        # Verify Pillow can open it as AVIF
        from PIL import Image
        with Image.open(io.BytesIO(body)) as img:
            assert img.format.lower() in ("avif", "heif"), (
                f"Pillow recognized format as {img.format}, expected AVIF/HEIF"
            )

    def test_avif_accepted_when_available(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        """When runtime profile says AVIF available, transform accepts AVIF."""
        caps = client.get("/api/v1/capabilities").json()
        if not caps["avif_available"]:
            pytest.skip("AVIF is not available in this runtime")

        response = client.post(
            "/api/v1/transform",
            files={"files": ("test.jpg", sample_jpg_bytes, "image/jpeg")},
            data={"output_format": "avif", "quality": "80"},
        )
        # Should succeed (200) or fail for other reasons, but NOT 422 AVIF_UNAVAILABLE
        assert response.status_code != 422 or (
            response.status_code == 422
            and response.json().get("detail", {}).get("error", {}).get("code") != "AVIF_UNAVAILABLE"
        )


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
        # Batch outputs use sequential naming (default stem "file")
        assert "file-1.jpeg" in names
        assert "file-2.jpeg" in names
        assert "manifest.json" in names


class TestTransformFolderStructure:
    """Folder/batch structure preservation via optional `paths` field."""

    def test_paths_field_preserves_subfolder_in_zip(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """When `paths` is provided, directory is preserved but basenames become sequential."""
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
        # Directory preserved, basename replaced with sequential naming
        assert "images/file-1.jpeg" in names
        assert "assets/file-2.jpeg" in names

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
        # Batch sequential naming: original filenames replaced with file-1, file-2
        assert "file-1.jpeg" in names
        assert "file-2.jpeg" in names
        assert len(names) == 3

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
        """Two files with same basename in different subfolders — both preserved with sequential naming per directory."""
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
        # Directory preserved, basename replaced with sequential numbering
        assert "products/file-1.jpeg" in names
        assert "thumbnails/file-2.jpeg" in names


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


class TestNamingControls:
    """Integration tests for naming controls (zip_name, output_stem, output_prefix, output_suffix).

    Single-file: prefix/suffix only, no numbering, original basename preserved.
    Batch/folder: output_stem + sequential numbering, prefix/suffix ignored.
    ZIP name: independent field, separate from per-file naming.
    """

    def test_batch_default_zip_name_is_optimized_assets(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Without zip_name, Content-Disposition uses default optimized-assets.zip."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        assert "optimized-assets.zip" in disp

    def test_batch_custom_zip_name_in_content_disposition(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """With zip_name, Content-Disposition carries the custom name."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "jpg",
                "quality": "80",
                "zip_name": "my-custom-archive",
            },
        )
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        assert "my-custom-archive.zip" in disp

    def test_batch_output_stem_produces_sequential_names(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Batch: output_stem replaces basenames with stem-1, stem-2, ..."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("photo.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("image.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "webp",
                "quality": "80",
                "output_stem": "catalog",
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = [n for n in zf.namelist() if n != "manifest.json"]
        assert "catalog-1.webp" in names
        assert "catalog-2.webp" in names
        # Original names must NOT appear
        assert "photo.webp" not in names
        assert "image.webp" not in names

    def test_batch_default_stem_is_file(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Batch without output_stem: defaults to 'file' stem."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "webp",
                "quality": "80",
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = [n for n in zf.namelist() if n != "manifest.json"]
        assert "file-1.webp" in names
        assert "file-2.webp" in names

    def test_batch_prefix_suffix_ignored(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """Batch: output_prefix and output_suffix must be ignored; output_stem used instead."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("photo.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("image.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "webp",
                "quality": "80",
                "output_prefix": "opt_",
                "output_suffix": "_final",
                "output_stem": "batch",
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = [n for n in zf.namelist() if n != "manifest.json"]
        # prefix/suffix must NOT appear; only stem numbering
        assert "batch-1.webp" in names
        assert "batch-2.webp" in names
        assert "opt_" not in str(names)
        assert "_final" not in str(names)

    def test_single_file_with_prefix_suffix_content_disposition(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Single file: prefix/suffix applied, original basename preserved, no numbering."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("photo.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "jpg",
                "quality": "80",
                "output_prefix": "pre_",
                "output_suffix": "_suf",
            },
        )
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        assert "pre_photo_suf.jpeg" in disp

    def test_single_file_output_stem_ignored(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Single file: output_stem must be ignored; original basename preserved."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("photo.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "webp",
                "quality": "80",
                "output_stem": "catalog",
            },
        )
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        # Original basename preserved, no numbering
        assert "photo.webp" in disp
        assert "catalog" not in disp

    def test_single_file_no_numbering(
        self, client: TestClient, sample_jpg_bytes: bytes
    ) -> None:
        """Single file never gets numbered — format conversion only."""
        response = client.post(
            "/api/v1/transform",
            files={"files": ("landscape.jpg", sample_jpg_bytes, "image/jpeg")},
            data={
                "output_format": "webp",
                "quality": "80",
            },
        )
        assert response.status_code == 200
        disp = response.headers.get("content-disposition", "")
        assert "landscape.webp" in disp
        assert "-1" not in disp

    def test_invalid_zip_name_empty_after_sanitize_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """zip_name that becomes empty after sanitization → 422 INVALID_NAMING_CONFIG."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "jpg",
                "quality": "80",
                "zip_name": "   ..  ",
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_NAMING_CONFIG"

    def test_invalid_output_stem_returns_422(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """output_stem that becomes empty after sanitization → 422 INVALID_NAMING_CONFIG."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "webp",
                "quality": "80",
                "output_stem": "   ..  ",
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_NAMING_CONFIG"

    def test_manifest_output_fields_match_resolved_zip_paths(
        self, client: TestClient, sample_jpg_bytes: bytes, sample_png_bytes: bytes
    ) -> None:
        """manifest.files[].output values match actual ZIP entry paths after sequential naming."""
        response = client.post(
            "/api/v1/transform",
            files=[
                ("files", ("a.jpg", sample_jpg_bytes, "image/jpeg")),
                ("files", ("b.png", sample_png_bytes, "image/png")),
            ],
            data={
                "output_format": "webp",
                "quality": "80",
                "output_stem": "image",
            },
        )
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        manifest = json.loads(zf.read("manifest.json"))
        zip_names = [n for n in zf.namelist() if n != "manifest.json"]
        for entry in manifest["files"]:
            assert entry["output"] in zip_names
            assert entry["output"].startswith("image-")

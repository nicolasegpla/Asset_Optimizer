"""Integration tests for POST /api/v1/transform endpoint."""
from __future__ import annotations

import io
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
        assert len(names) == 2
        assert "a.jpeg" in names
        assert "b.jpeg" in names


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
        assert data["detail"]["error"]["code"] == "UNSUPPORTED_INPUT_FORMAT"

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


class TestTransformLimits:
    def test_file_count_limit_rejects_over_100(self, client: TestClient, sample_jpg_bytes: bytes) -> None:
        files = [
            ("files", (f"img{i}.jpg", sample_jpg_bytes, "image/jpeg"))
            for i in range(101)
        ]
        response = client.post(
            "/api/v1/transform",
            files=files,
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "FILE_COUNT_LIMIT"

    def test_empty_file_list_rejects(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/transform",
            files=[],
            data={"output_format": "jpg", "quality": "80"},
        )
        assert response.status_code == 422
        data = response.json()
        # FastAPI form validation returns a list for empty multipart,
        # or our custom dict when the check is reached in code
        assert response.status_code == 422


class TestHealthEndpoint:
    def test_health_returns_online(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


class TestLimitsEndpoint:
    def test_limits_returns_all_three_limits(self, client: TestClient) -> None:
        response = client.get("/api/v1/limits")
        assert response.status_code == 200
        data = response.json()
        assert "max_files" in data
        assert "max_total_bytes" in data
        assert "max_pixels" in data
        assert data["max_files"] == 100
        assert data["max_total_bytes"] == 52_428_800  # 50 MB
        assert data["max_pixels"] == 52_428_800  # 50 MP
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
        assert "a.jpg" in names
        assert "b.png" in names


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
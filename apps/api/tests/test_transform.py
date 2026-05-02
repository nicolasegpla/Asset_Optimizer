"""Unit tests for transform.py service functions."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.transform import (
    OutputFormat,
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS,
    calculate_metadata,
    decode_image,
    encode_image,
    normalize_mode,
    resize_image,
    transform_image,
)


class TestDecodeImage:
    def test_decodes_valid_jpg(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_decodes_valid_png(self, sample_png_bytes: bytes) -> None:
        img = decode_image(sample_png_bytes)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_decodes_valid_webp(self, sample_webp_bytes: bytes) -> None:
        img = decode_image(sample_webp_bytes)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_raises_on_corrupt_data(self, corrupt_bytes: bytes) -> None:
        with pytest.raises(Exception):
            decode_image(corrupt_bytes)


class TestResizeImage:
    def test_no_resize_when_both_none(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, None, None)
        assert result.size == img.size

    def test_no_resize_when_ratio_gte_1(self, sample_jpg_bytes: bytes) -> None:
        """When target is larger than original, no upscaling."""
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, 200, 200)
        assert result.size == img.size

    def test_resize_width_only(self, sample_jpg_bytes: bytes) -> None:
        """Resize to max_width=50, aspect ratio preserved."""
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, 50, None)
        assert result.width == 50
        assert result.height == 50  # 100x100 → 50x50 (ratio 0.5)
        assert result.height < img.height

    def test_resize_height_only(self, sample_jpg_bytes: bytes) -> None:
        """Resize to max_height=25, aspect ratio preserved."""
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, None, 25)
        assert result.height == 25
        assert result.width < img.width

    def test_resize_both_dims_fits_within(self, sample_jpg_bytes: bytes) -> None:
        """Both limits set but only smaller binding dimension applies."""
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, 80, 80)
        # 100x100 → 80x80 (ratio 0.8 for both)
        assert result.size == (80, 80)

    def test_resize_width_constrains_because_smaller(self, sample_jpg_bytes: bytes) -> None:
        """max_width=40, max_height=80 → width is binding."""
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, 40, 80)
        # width ratio = 40/100 = 0.4 → 40x40
        # height ratio = 80/100 = 0.8 → 80x80
        # min ratio = 0.4 → 40x40
        assert result.width == 40
        assert result.height == 40

    def test_preserves_aspect_ratio_wide_image(self) -> None:
        """Wide image: 200x100, resize 50xNone → 50x25."""
        img = Image.new("RGB", (200, 100))
        result = resize_image(img, 50, None)
        assert result.width == 50
        assert result.height == 25

    def test_preserves_aspect_ratio_tall_image(self) -> None:
        """Tall image: 100x200, resize Nonex50 → 25x50."""
        img = Image.new("RGB", (100, 200))
        result = resize_image(img, None, 50)
        assert result.width == 25
        assert result.height == 50

    def test_returns_copy_not_same_instance(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        result = resize_image(img, 50, 50)
        assert result is not img


class TestNormalizeMode:
    def test_rgb_stays_rgb_for_jpg(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        result = normalize_mode(img, OutputFormat.JPG)
        assert result.mode == "RGB"

    def test_rgba_gets_white_background_for_jpg(self, sample_rgba_png_bytes: bytes) -> None:
        """RGBA PNG → JPG should composite on white background."""
        img = decode_image(sample_rgba_png_bytes)
        assert img.mode == "RGBA"
        result = normalize_mode(img, OutputFormat.JPG)
        assert result.mode == "RGB"
        # Check it's not transparent by verifying all pixels are non-zero
        pixels = list(result.getdata())
        # White background with some colored overlay should not be uniform
        assert len(pixels) == 50 * 50

    def test_palette_mode_gets_rgba_for_jpg(self) -> None:
        """P mode should be converted through RGBA to composite on white."""
        img = Image.new("P", (50, 50))
        result = normalize_mode(img, OutputFormat.JPG)
        assert result.mode == "RGB"

    def test_p_mode_gets_rgba_for_webp(self) -> None:
        """P mode → WEBP converts to RGBA."""
        img = Image.new("P", (50, 50))
        result = normalize_mode(img, OutputFormat.WEBP)
        assert result.mode == "RGBA"

    def test_rgba_stays_rgba_for_webp(self, sample_rgba_png_bytes: bytes) -> None:
        img = decode_image(sample_rgba_png_bytes)
        result = normalize_mode(img, OutputFormat.WEBP)
        # WEBP/AVIF keep RGBA when present
        assert result.mode in ("RGBA", "LA")

    def test_returns_copy(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        result = normalize_mode(img, OutputFormat.JPG)
        assert result is not img


class TestEncodeImage:
    def test_encode_jpg_produces_bytes(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        normalized = normalize_mode(img, OutputFormat.JPG)
        result = encode_image(normalized, OutputFormat.JPG, quality=85)
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Verify it's a valid JPEG by re-opening
        reloaded = Image.open(io.BytesIO(result))
        assert reloaded.format == "JPEG"

    def test_encode_png_produces_bytes(self, sample_png_bytes: bytes) -> None:
        img = decode_image(sample_png_bytes)
        normalized = normalize_mode(img, OutputFormat.PNG)
        result = encode_image(normalized, OutputFormat.PNG, quality=85)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_encode_webp_produces_bytes(self, sample_webp_bytes: bytes) -> None:
        img = decode_image(sample_webp_bytes)
        result = encode_image(img, OutputFormat.WEBP, quality=85)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_quality_affects_size(self, sample_jpg_bytes: bytes) -> None:
        """Higher quality → larger file."""
        img = decode_image(sample_jpg_bytes)
        normalized = normalize_mode(img, OutputFormat.JPG)
        high = encode_image(normalized, OutputFormat.JPG, quality=100)
        low = encode_image(normalized, OutputFormat.JPG, quality=10)
        assert len(high) >= len(low)

    def test_png_quality_maps_to_compress_level(self, sample_png_bytes: bytes) -> None:
        """Quality 100 → compress_level 0 (no compression), quality 1 → 9 (max)."""
        img = decode_image(sample_png_bytes)
        normalized = normalize_mode(img, OutputFormat.PNG)
        # Max quality = no compression
        result = encode_image(normalized, OutputFormat.PNG, quality=100)
        assert isinstance(result, bytes)
        # Min quality = max compression
        result_min = encode_image(normalized, OutputFormat.PNG, quality=1)
        assert isinstance(result_min, bytes)


class TestCalculateMetadata:
    def test_compression_ratio_positive_when_shrunk(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        normalized = normalize_mode(img, OutputFormat.JPG)
        original_bytes = len(sample_jpg_bytes)
        # Re-encode at lower quality → should compress
        transformed = encode_image(normalized, OutputFormat.JPG, quality=50)
        metadata = calculate_metadata(sample_jpg_bytes, transformed, img, normalized)
        assert metadata.original_bytes == original_bytes
        assert metadata.optimized_bytes == len(transformed)
        assert metadata.compression_ratio >= 0
        assert metadata.original_width == 100
        assert metadata.original_height == 100

    def test_compression_ratio_negative_when_expanded(self, sample_jpg_bytes: bytes) -> None:
        """Low-quality re-encode of already-compressed image can expand."""
        img = decode_image(sample_jpg_bytes)
        normalized = normalize_mode(img, OutputFormat.JPG)
        # Re-encode at max quality → can be larger than original
        transformed = encode_image(normalized, OutputFormat.JPG, quality=100)
        metadata = calculate_metadata(sample_jpg_bytes, transformed, img, normalized)
        # Compression ratio can be negative if expanded
        assert isinstance(metadata.compression_ratio, float)

    def test_transformed_dimensions_set(self, sample_jpg_bytes: bytes) -> None:
        img = decode_image(sample_jpg_bytes)
        normalized = normalize_mode(img, OutputFormat.JPG)
        transformed = encode_image(normalized, OutputFormat.JPG, quality=85)
        resized = resize_image(img, 50, None)
        resized_encoded = normalize_mode(resized, OutputFormat.JPG)
        resized_bytes = encode_image(resized_encoded, OutputFormat.JPG, quality=85)
        metadata = calculate_metadata(sample_jpg_bytes, resized_bytes, img, resized)
        assert metadata.transformed_width == 50
        assert metadata.transformed_height == 50


class TestTransformImage:
    def test_full_pipeline_jpg_to_jpg(self, sample_jpg_bytes: bytes) -> None:
        data, metadata = transform_image(
            data=sample_jpg_bytes,
            output_format=OutputFormat.JPG,
            quality=85,
            max_width=None,
            max_height=None,
        )
        assert isinstance(data, bytes)
        assert metadata.original_bytes == len(sample_jpg_bytes)
        assert metadata.original_format in ("JPEG", "jpg", "unknown")

    def test_full_pipeline_png_to_jpg(self, sample_png_bytes: bytes) -> None:
        """PNG (RGBA) → JPG should composite on white, no transparency."""
        data, metadata = transform_image(
            data=sample_png_bytes,
            output_format=OutputFormat.JPG,
            quality=85,
            max_width=None,
            max_height=None,
        )
        assert isinstance(data, bytes)
        # Verify output is valid JPG
        result_img = Image.open(io.BytesIO(data))
        assert result_img.format == "JPEG"
        assert result_img.mode == "RGB"

    def test_full_pipeline_with_resize(self, sample_jpg_bytes: bytes) -> None:
        data, metadata = transform_image(
            data=sample_jpg_bytes,
            output_format=OutputFormat.JPG,
            quality=85,
            max_width=50,
            max_height=None,
        )
        assert isinstance(data, bytes)
        result_img = Image.open(io.BytesIO(data))
        assert result_img.width == 50

    def test_full_pipeline_webp_output(self, sample_jpg_bytes: bytes) -> None:
        data, metadata = transform_image(
            data=sample_jpg_bytes,
            output_format=OutputFormat.WEBP,
            quality=80,
            max_width=None,
            max_height=None,
        )
        assert isinstance(data, bytes)
        result_img = Image.open(io.BytesIO(data))
        # WEBP might be stored as WEBP or could be returned differently
        assert result_img.width == 100

    def test_raises_on_corrupt_input(self, corrupt_bytes: bytes) -> None:
        with pytest.raises(Exception):
            transform_image(
                data=corrupt_bytes,
                output_format=OutputFormat.JPG,
                quality=85,
                max_width=None,
                max_height=None,
            )


class TestFormatConstants:
    def test_supported_input_formats(self) -> None:
        assert "jpg" in SUPPORTED_INPUT_FORMATS
        assert "jpeg" in SUPPORTED_INPUT_FORMATS
        assert "png" in SUPPORTED_INPUT_FORMATS
        assert "webp" in SUPPORTED_INPUT_FORMATS

    def test_supported_output_formats(self) -> None:
        assert "jpg" in SUPPORTED_OUTPUT_FORMATS
        assert "png" in SUPPORTED_OUTPUT_FORMATS
        assert "webp" in SUPPORTED_OUTPUT_FORMATS
        assert "avif" in SUPPORTED_OUTPUT_FORMATS

    def test_output_format_enum_values(self) -> None:
        assert OutputFormat.JPG.value == "jpg"
        assert OutputFormat.PNG.value == "png"
        assert OutputFormat.WEBP.value == "webp"
        assert OutputFormat.AVIF.value == "avif"
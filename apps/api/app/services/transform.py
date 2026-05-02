"""Pure image transformation functions — no FastAPI imports."""
from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from PIL import Image


class OutputFormat(str, Enum):
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"


SUPPORTED_INPUT_FORMATS = frozenset({"jpg", "jpeg", "png", "webp"})
SUPPORTED_OUTPUT_FORMATS = frozenset({"jpg", "png", "webp", "avif"})


@dataclass(frozen=True)
class ImageMetadata:
    original_bytes: int
    optimized_bytes: int
    compression_ratio: float
    original_width: int
    original_height: int
    original_format: str
    transformed_width: int | None = None
    transformed_height: int | None = None


def decode_image(data: bytes) -> Image.Image:
    """Decode bytes into a PIL Image."""
    return Image.open(io.BytesIO(data))


def calculate_metadata(
    original_data: bytes,
    transformed_data: bytes,
    original_img: Image.Image,
    transformed_img: Image.Image,
) -> ImageMetadata:
    """Calculate compression metadata."""
    return ImageMetadata(
        original_bytes=len(original_data),
        optimized_bytes=len(transformed_data),
        compression_ratio=round(
            (1 - len(transformed_data) / len(original_data)) * 100, 2
        ),
        original_width=original_img.width,
        original_height=original_img.height,
        original_format=original_img.format or "unknown",
        transformed_width=transformed_img.width,
        transformed_height=transformed_img.height,
    )


def resize_image(img: Image.Image, max_width: int | None, max_height: int | None) -> Image.Image:
    """
    Resize image preserving aspect ratio, never upscaling.
    If both dimensions are None, return unchanged copy.
    """
    if max_width is None and max_height is None:
        return img.copy()

    current_width, current_height = img.size

    # Calculate target dimensions fitting within bounds
    target_width = max_width
    target_height = max_height

    if target_width is not None and target_height is not None:
        ratio = min(target_width / current_width, target_height / current_height)
    elif target_width is not None:
        ratio = target_width / current_width
    else:
        ratio = target_height / current_height

    # Prevent upscaling
    if ratio >= 1:
        return img.copy()

    new_width = int(round(current_width * ratio))
    new_height = int(round(current_height * ratio))

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def normalize_mode(img: Image.Image, output_format: OutputFormat) -> Image.Image:
    """
    Normalize image mode for output format.
    PNG supports RGBA directly.
    JPG requires RGB (no transparency) — composite on white background.
    WEBP/AVIF: keep RGBA if present, encoder handles it.
    """
    if output_format == OutputFormat.JPG:
        if img.mode in ("RGBA", "LA", "P"):
            # White background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            return background
        if img.mode != "RGB":
            return img.convert("RGB")
        return img.copy()
    elif img.mode == "P":
        return img.convert("RGBA")
    return img.copy()


def encode_image(img: Image.Image, output_format: OutputFormat, quality: int) -> bytes:
    """
    Encode image to target format with given quality.
    PNG quality maps to compress_level (0-9), not a 1-100 scale.
    """
    buffer = io.BytesIO()

    if output_format == OutputFormat.PNG:
        # PNG: quality param maps to compress_level (0=none, 9=max)
        # compress_level = max(0, 9 - floor(quality / 12))
        # quality=100 → compress_level=0 (no compression), quality=1 → compress_level=9 (max)
        compress_level = max(0, 9 - int(quality // 12))
        img.save(buffer, format="PNG", compress_level=compress_level)
    elif output_format == OutputFormat.WEBP:
        img.save(buffer, format="WEBP", quality=quality)
    elif output_format == OutputFormat.AVIF:
        img.save(buffer, format="AVIF", quality=quality)
    else:
        # JPG
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

    buffer.seek(0)
    return buffer.getvalue()


def transform_image(
    data: bytes,
    output_format: OutputFormat,
    quality: int,
    max_width: int | None,
    max_height: int | None,
) -> tuple[bytes, ImageMetadata]:
    """
    Full transformation pipeline: verify → resize → normalize mode → encode → metadata.
    """
    # Verify format by decoding
    original_img = decode_image(data)

    # Resize (no upscaling)
    resized = resize_image(original_img, max_width, max_height)

    # Normalize mode for output format
    normalized = normalize_mode(resized, output_format)

    # Encode
    encoded = encode_image(normalized, output_format, quality)

    # Metadata
    metadata = calculate_metadata(data, encoded, original_img, normalized)

    return encoded, metadata

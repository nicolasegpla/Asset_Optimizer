"""Unit tests for app.services.naming."""
from __future__ import annotations

import pytest

from app.services.naming import (
    NamingConfig,
    _sanitize_field,
    resolve_single_output_name,
    resolve_batch_output_name,
    resolve_zip_name,
    sanitize_naming_config,
)


class TestSanitizeField:
    """Tests for _sanitize_field helper."""

    def test_none_returns_empty_string(self) -> None:
        assert _sanitize_field(None) == ""

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert _sanitize_field("  hello  ") == "hello"

    def test_strips_leading_trailing_dots(self) -> None:
        assert _sanitize_field("..hello..") == "hello"

    def test_removes_disallowed_chars(self) -> None:
        # Colon (:) is among disallowed chars and is removed entirely
        assert _sanitize_field("file<name>test") == "filenametest"
        assert _sanitize_field('file"name:test') == "filenametest"
        assert _sanitize_field("file/name\\test") == "filenametest"
        assert _sanitize_field("file|name?test*") == "filenametest"

    def test_collapse_internal_spaces(self) -> None:
        assert _sanitize_field("file  name   test") == "file name test"

    def test_max_length_raises(self) -> None:
        long_value = "a" * 129
        with pytest.raises(ValueError, match="exceeds maximum length"):
            _sanitize_field(long_value)

    def test_exactly_128_chars_ok(self) -> None:
        value = "a" * 128
        assert _sanitize_field(value) == value

    def test_empty_after_sanitize_raises(self) -> None:
        with pytest.raises(ValueError, match="empty after sanitization"):
            _sanitize_field("   ..  ")

    def test_control_chars_removed(self) -> None:
        # tab, newline, carriage return
        assert _sanitize_field("file\t\n\rname") == "filename"


class TestSanitizeNamingConfig:
    """Tests for sanitize_naming_config()."""

    def test_all_none_returns_config_with_nones(self) -> None:
        config = sanitize_naming_config(None, None, None, None)
        assert config.zip_name is None
        assert config.output_prefix is None
        assert config.output_suffix is None
        assert config.output_stem is None

    def test_valid_values_preserved(self) -> None:
        config = sanitize_naming_config("my-zip", "pre_", "_suf", "catalog")
        assert config.zip_name == "my-zip"
        assert config.output_prefix == "pre_"
        assert config.output_suffix == "_suf"
        assert config.output_stem == "catalog"

    def test_empty_zip_name_raises(self) -> None:
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_naming_config("   ..  ", None, None, None)

    def test_long_zip_name_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_naming_config("a" * 129, None, None, None)

    def test_long_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_naming_config(None, "b" * 129, None, None)

    def test_long_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_naming_config(None, None, "c" * 129, None)

    def test_long_output_stem_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_naming_config(None, None, None, "d" * 129)


class TestResolveZipName:
    """Tests for resolve_zip_name()."""

    def test_none_returns_default(self) -> None:
        assert resolve_zip_name(None) == "optimized-assets.zip"

    def test_stem_appended_with_zip_extension(self) -> None:
        assert resolve_zip_name("my-custom-zip") == "my-custom-zip.zip"

    def test_extension_stripped(self) -> None:
        # _strip_extension strips the last dot-extension, so .gz is stripped from my-zip.tar.gz
        assert resolve_zip_name("my-zip.tar.gz") == "my-zip.tar.zip"

    def test_sanitization_applied(self) -> None:
        assert resolve_zip_name("my  zip") == "my zip.zip"

    def test_disallowed_chars_sanitized(self) -> None:
        assert resolve_zip_name("my<zip>name") == "myzipname.zip"

    def test_empty_after_sanitize_raises(self) -> None:
        with pytest.raises(ValueError, match="empty after sanitization"):
            resolve_zip_name("   ..  ")


class TestResolveSingleOutputName:
    """Tests for resolve_single_output_name() — single-file naming preserves original basename."""

    def test_no_prefix_suffix_preserves_basename(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem=None)
        result = resolve_single_output_name("photo.jpg", config, "webp")
        assert result == "photo.webp"

    def test_prefix_prepended_to_stem(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix="sm_", output_suffix=None, output_stem=None)
        result = resolve_single_output_name("photo.jpg", config, "jpg")
        assert result == "sm_photo.jpeg"

    def test_suffix_appended_before_ext(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix="_300w", output_stem=None)
        result = resolve_single_output_name("hero.jpg", config, "webp")
        assert result == "hero_300w.webp"

    def test_prefix_and_suffix_combined(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix="sm_", output_suffix="_opt", output_stem=None)
        result = resolve_single_output_name("photo.webp", config, "png")
        assert result == "sm_photo_opt.png"

    def test_directory_preserved(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix="out_", output_suffix=None, output_stem=None)
        result = resolve_single_output_name("assets/photo.jpg", config, "jpg")
        assert result == "assets/out_photo.jpeg"

    def test_subdirectory_preserved(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix="out_", output_suffix=None, output_stem=None)
        result = resolve_single_output_name("images/thumbs/photo.png", config, "jpg")
        assert result == "images/thumbs/out_photo.jpeg"

    def test_jpg_extension_normalized(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem=None)
        result = resolve_single_output_name("photo.jpg", config, "jpg")
        assert result == "photo.jpeg"

    def test_avif_extension_preserved(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem=None)
        result = resolve_single_output_name("photo.png", config, "avif")
        assert result == "photo.avif"

    def test_output_stem_ignored_for_single(self) -> None:
        """output_stem must not affect single-file naming."""
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="catalog")
        result = resolve_single_output_name("photo.jpg", config, "webp")
        assert result == "photo.webp"  # stem NOT applied

    def test_suffix_with_dot_preserved(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=".final", output_stem=None)
        result = resolve_single_output_name("photo.jpg", config, "jpg")
        assert result == "photo.final.jpeg"


class TestResolveBatchOutputName:
    """Tests for resolve_batch_output_name() — batch naming replaces basename with {stem}-{N}."""

    def test_custom_stem_sequential_numbers(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="catalog")
        assert resolve_batch_output_name("photo.jpg", config, "webp", 1) == "catalog-1.webp"
        assert resolve_batch_output_name("photo.jpg", config, "webp", 2) == "catalog-2.webp"
        assert resolve_batch_output_name("photo.jpg", config, "webp", 3) == "catalog-3.webp"

    def test_default_stem_is_file(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem=None)
        assert resolve_batch_output_name("photo.jpg", config, "avif", 1) == "file-1.avif"
        assert resolve_batch_output_name("photo.jpg", config, "avif", 2) == "file-2.avif"

    def test_directory_preserved_basename_replaced(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="product")
        result = resolve_batch_output_name("photos/img1.png", config, "webp", 1)
        assert result == "photos/product-1.webp"

    def test_deep_directory_preserved(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="thumb")
        result = resolve_batch_output_name("a/b/c/hero.png", config, "jpg", 2)
        assert result == "a/b/c/thumb-2.jpeg"

    def test_prefix_and_suffix_ignored_for_batch(self) -> None:
        """prefix/suffix must not affect batch naming."""
        config = NamingConfig(zip_name=None, output_prefix="opt_", output_suffix="_final", output_stem="batch")
        result = resolve_batch_output_name("photo.jpg", config, "webp", 1)
        assert result == "batch-1.webp"  # prefix/suffix ignored

    def test_jpg_normalized(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="img")
        result = resolve_batch_output_name("photo.jpg", config, "jpg", 1)
        assert result == "img-1.jpeg"

    def test_sequence_number_starts_at_one(self) -> None:
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="file")
        assert resolve_batch_output_name("a.jpg", config, "png", 1) == "file-1.png"

    def test_all_same_original_names_get_sequential(self) -> None:
        """All files originally named the same should get sequential numbers — no collisions."""
        config = NamingConfig(zip_name=None, output_prefix=None, output_suffix=None, output_stem="catalog")
        results = [
            resolve_batch_output_name("photo.png", config, "webp", i)
            for i in range(1, 6)
        ]
        assert results == ["catalog-1.webp", "catalog-2.webp", "catalog-3.webp", "catalog-4.webp", "catalog-5.webp"]

"""Unit tests for upload path resolution and validation."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.upload_paths import resolve_upload_paths


class FakeUploadFile:
    """Minimal UploadFile stand-in for tests."""

    def __init__(self, filename: str) -> None:
        self.filename = filename


class TestResolveUploadPathsCanonicalArray:
    """Canonical ordered-array payload."""

    def test_parses_ordered_array(self) -> None:
        files = [FakeUploadFile("a.jpg"), FakeUploadFile("b.jpg")]
        paths_raw = '["subdir/a.jpg", "other/b.jpg"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["subdir/a.jpg", "other/b.jpg"]

    def test_strips_empty_and_dot_segments(self) -> None:
        files = [FakeUploadFile("img.png")]
        paths_raw = '["././subdir/./img.png"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["subdir/img.png"]

    def test_normalizes_forward_slash_in_paths(self) -> None:
        """Forward slashes are preserved as-is (actual browser behavior)."""
        files = [FakeUploadFile("photo.jpg")]
        paths_raw = '["folder/subfolder/photo.jpg"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["folder/subfolder/photo.jpg"]

    def test_rejects_absolute_path(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        paths_raw = '["/absolute/path/test.jpg"]'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422
        assert "absolute paths are not allowed" in str(exc_info.value.detail)

    def test_rejects_drive_prefix(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        paths_raw = '["C:/Users/test.jpg"]'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422
        assert "drive prefixes are not allowed" in str(exc_info.value.detail)

    def test_rejects_traversal(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        paths_raw = '["subdir/../etc/passwd.jpg"]'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422
        assert "'..' path traversal is not allowed" in str(exc_info.value.detail)

    def test_rejects_traversal_in_array(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        paths_raw = '["a/../b/test.jpg"]'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422

    def test_basename_mismatch_uses_uploaded_filename(self) -> None:
        files = [FakeUploadFile("photo.jpg")]
        paths_raw = '["subdir/wrongname.jpg"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["subdir/photo.jpg"]

    def test_array_length_not_equal_file_count_rejected(self) -> None:
        files = [FakeUploadFile("a.jpg"), FakeUploadFile("b.jpg")]
        paths_raw = '["only-one.jpg"]'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422
        assert "must match file count" in str(exc_info.value.detail)

    def test_malformed_json_rejected(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        paths_raw = "not json at all"
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422
        assert "must be valid JSON" in str(exc_info.value.detail)


class TestResolveUploadPathsLegacyObject:
    """Legacy filename-keyed object payload (backward compat)."""

    def test_parses_legacy_object(self) -> None:
        files = [FakeUploadFile("a.jpg"), FakeUploadFile("b.jpg")]
        paths_raw = '{"a.jpg": "subdir/a.jpg", "b.jpg": "other/b.jpg"}'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["subdir/a.jpg", "other/b.jpg"]

    def test_uses_filename_when_key_missing(self) -> None:
        files = [FakeUploadFile("photo.jpg")]
        paths_raw = '{"other.jpg": "subdir/other.jpg"}'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["photo.jpg"]

    def test_legacy_object_still_validates_traversal(self) -> None:
        files = [FakeUploadFile("a.jpg")]
        paths_raw = '{"a.jpg": "subdir/../../../etc/passwd.jpg"}'
        with pytest.raises(HTTPException) as exc_info:
            resolve_upload_paths(files, paths_raw)
        assert exc_info.value.status_code == 422


class TestResolveUploadPathsBackwardCompat:
    """Missing paths_raw returns None for backward compat."""

    def test_none_returns_none(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        result = resolve_upload_paths(files, None)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        files = [FakeUploadFile("test.jpg")]
        result = resolve_upload_paths(files, "")
        assert result is None

    def test_empty_array_is_valid(self) -> None:
        files: list[FakeUploadFile] = []
        result = resolve_upload_paths(files, "[]")
        assert result == []


class TestSanitizePathSegments:
    """Edge cases in path segment normalization."""

    def test_strips_leading_dot_slash(self) -> None:
        files = [FakeUploadFile("test.png")]
        paths_raw = '["./subdir/./test.png"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["subdir/test.png"]

    def test_adjacent_slashes_collapsed(self) -> None:
        files = [FakeUploadFile("x.jpg")]
        paths_raw = '["a//b//c/x.jpg"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["a/b/c/x.jpg"]

    def test_deeply_nested_preserved(self) -> None:
        files = [FakeUploadFile("img.jpg")]
        paths_raw = '["a/b/c/d/e/img.jpg"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["a/b/c/d/e/img.jpg"]

    def test_single_file_in_subdir(self) -> None:
        files = [FakeUploadFile("logo.png")]
        paths_raw = '["assets/logos/logo.png"]'
        result = resolve_upload_paths(files, paths_raw)
        assert result == ["assets/logos/logo.png"]

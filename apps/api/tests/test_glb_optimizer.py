"""Unit tests for glb_optimizer.py service functions."""
from __future__ import annotations

import asyncio
import json
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.glb_optimizer import (
    GlbOptimizationMetadata,
    GLB_MAGIC,
    GLB_OPTIMIZATION_TIMEOUT,
    optimize_glb,
    validate_glb_magic,
)


def make_minimal_glb() -> bytes:
    """Create a minimal valid GLB file for testing."""
    gltf_json = json.dumps({
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": []
    }).encode("utf-8")

    json_padding = (4 - (len(gltf_json) % 4)) % 4
    gltf_json += b" " * json_padding

    json_chunk_len = len(gltf_json)
    json_chunk_type = 0x4E4F534A

    magic = b"glTF"
    version = struct.pack("<I", 2)
    length = struct.pack("<I", 12 + 8 + json_chunk_len)

    json_chunk = struct.pack("<I", json_chunk_len) + struct.pack("<I", json_chunk_type) + gltf_json

    return magic + version + length + json_chunk


class TestValidateGlbMagic:
    """Tests for validate_glb_magic function."""

    def test_valid_glb_passes(self) -> None:
        """A valid GLB file with correct magic bytes passes validation."""
        data = make_minimal_glb()
        # Should not raise
        validate_glb_magic(data)

    def test_empty_data_raises(self) -> None:
        """Empty data should raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            validate_glb_magic(b"")

    def test_too_short_data_raises(self) -> None:
        """Data shorter than 4 bytes should raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            validate_glb_magic(b"glT")

    def test_wrong_magic_bytes_raises(self) -> None:
        """Data without 'glTF' magic should raise ValueError."""
        with pytest.raises(ValueError, match="missing 'glTF' magic"):
            validate_glb_magic(b"NOTAVALIDFILE")

    def test_corrupt_glb_raises(self) -> None:
        """Data with wrong first 4 bytes should raise ValueError."""
        data = b"XXXX" + b"\x00" * 100
        with pytest.raises(ValueError, match="missing 'glTF' magic"):
            validate_glb_magic(data)

    @pytest.mark.parametrize("magic", [
        b"glTF",  # correct
    ])
    def test_correct_magic_passes(self, magic: bytes) -> None:
        """Any data starting with 'glTF' magic should pass."""
        data = magic + b"\x00" * 100
        validate_glb_magic(data)

    @pytest.mark.parametrize("magic", [
        b"GLTF",
        b"gltf",
        b"GlTf",
        b"\x00\x00\x00\x00",
        b"GIF8",
    ])
    def test_incorrect_magic_raises(self, magic: bytes) -> None:
        """Data not starting with exactly 'glTF' should raise."""
        data = magic + b"\x00" * 100
        with pytest.raises(ValueError, match="missing 'glTF' magic"):
            validate_glb_magic(data)


class TestOptimizeGlb:
    """Tests for optimize_glb async function."""

    def test_successful_optimization(self) -> None:
        """When subprocess succeeds, return optimized data and metadata."""
        input_data = make_minimal_glb()
        fake_output = b"optimized glb content"

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_subprocess:
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", MagicMock()) as mock_open:
                    mock_file = MagicMock()
                    mock_file.read.return_value = fake_output
                    mock_open.return_value.__enter__.return_value = mock_file

                    result_data, metadata = asyncio.run(optimize_glb(input_data))

        assert result_data == fake_output
        assert isinstance(metadata, GlbOptimizationMetadata)
        assert metadata.original_bytes == len(input_data)
        assert metadata.optimized_bytes == len(fake_output)

    def test_subprocess_failure_raises(self) -> None:
        """When subprocess returns non-zero, raise RuntimeError."""
        input_data = make_minimal_glb()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"optimization failed"))
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(RuntimeError, match="GLB optimization failed"):
                    asyncio.run(optimize_glb(input_data))

    def test_timeout_raises(self) -> None:
        """When subprocess times out, raise RuntimeError."""
        input_data = make_minimal_glb()

        mock_proc = AsyncMock()
        # Simulate timeout by raising asyncio.TimeoutError
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="timed out"):
                asyncio.run(optimize_glb(input_data))

            # Verify cleanup
            mock_proc.kill.assert_called_once()

    def test_missing_output_file_raises(self) -> None:
        """When output file is missing after subprocess, raise RuntimeError."""
        input_data = make_minimal_glb()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(RuntimeError, match="did not produce output file"):
                    asyncio.run(optimize_glb(input_data))

    def test_command_includes_expected_flags(self) -> None:
        """Verify the subprocess command includes all expected flags."""
        input_data = make_minimal_glb()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_subprocess:
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", MagicMock()) as mock_open:
                    mock_file = MagicMock()
                    mock_file.read.return_value = b"optimized"
                    mock_open.return_value.__enter__.return_value = mock_file

                    asyncio.run(optimize_glb(input_data))

        # Check that create_subprocess_exec was called with the right command
        call_args = mock_subprocess.call_args
        cmd = call_args[0]
        assert "gltf-transform" in cmd[0]
        assert "optimize" in cmd
        assert "--compress" in cmd
        assert "draco" in cmd

    def test_temp_files_cleaned_up(self) -> None:
        """Verify temporary input/output files are cleaned up after optimization."""
        input_data = make_minimal_glb()
        removed_files: list[str] = []

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        def track_unlink(path: str) -> None:
            removed_files.append(path)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("os.path.exists", return_value=True):
                with patch("os.unlink", side_effect=track_unlink):
                    with patch("builtins.open", MagicMock()):
                        asyncio.run(optimize_glb(input_data))

        # Both input and output files should be removed
        assert len(removed_files) == 2

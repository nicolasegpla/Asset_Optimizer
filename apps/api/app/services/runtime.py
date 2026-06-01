"""Runtime capability profile — built once at startup, stored in app.state."""
from __future__ import annotations

import io
import logging
import subprocess
from dataclasses import dataclass, field

from PIL import Image

__all__ = ["RuntimeProfile", "build_runtime_profile", "probe_avif", "probe_gltf_transform"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeProfile:
    avif_available: bool
    gltf_transform_available: bool
    pillow_version: str
    dependency_status: dict[str, str]


def get_pillow_version() -> str:
    """Return the installed Pillow version string."""
    try:
        from PIL import __version__
        return __version__
    except Exception:
        return "unknown"


def get_dependency_status() -> dict[str, str]:
    """Return a snapshot of encoder availability statuses."""
    status: dict[str, str] = {}

    # Pillow
    try:
        from PIL import __version__
        status["pillow"] = f"ok ({__version__})"
    except Exception:
        status["pillow"] = "unavailable"

    # pillow-avif-plugin via import check
    try:
        from pillow_avif import is_available as _avif_check
        avail = _avif_check()
        status["avif_encoder"] = "ok" if avail else "unavailable"
    except ImportError:
        status["avif_encoder"] = "not installed"
    except Exception as e:
        status["avif_encoder"] = f"error: {e}"

    return status


def probe_avif() -> bool:
    """
    Perform a real in-memory AVIF encode to validate the encoder works.
    Returns True only if a minimal 1x1 RGB image can be saved as AVIF.
    """
    try:
        img = Image.new("RGB", (1, 1), color=(0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format="AVIF", quality=1)
        buffer.seek(0)
        # If we got bytes back, the encoder is functional
        return len(buffer.getvalue()) > 0
    except Exception as e:
        logger.debug("AVIF probe failed: %s", e)
        return False


def probe_gltf_transform() -> bool:
    """
    Probe whether the gltf-transform CLI is installed and callable.
    Returns True if `gltf-transform --version` exits 0.
    """
    try:
        result = subprocess.run(
            ["gltf-transform", "--version"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug("gltf-transform probe failed: %s", e)
        return False


def build_runtime_profile() -> RuntimeProfile:
    """Build the runtime profile: probe AVIF, collect version/status, return dataclass."""
    avif_available = probe_avif()
    gltf_transform_available = probe_gltf_transform()
    pillow_version = get_pillow_version()
    dependency_status = get_dependency_status()

    # Startup log
    logger.info(
        "Startup: AVIF=%s, gltf-transform=%s, Pillow=%s",
        avif_available,
        gltf_transform_available,
        pillow_version,
    )

    return RuntimeProfile(
        avif_available=avif_available,
        gltf_transform_available=gltf_transform_available,
        pillow_version=pillow_version,
        dependency_status=dependency_status,
    )
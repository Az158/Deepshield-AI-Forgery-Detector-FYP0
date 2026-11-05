"""
File Handler Utilities
=======================
Manages temporary files, output heatmap storage, and cleanup.
"""
import os
import uuid
import tempfile
import logging
from pathlib import Path

from config import OUTPUTS_DIR

logger = logging.getLogger(__name__)

# Ensure outputs directory exists
Path(OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)


def save_upload_to_temp(file_bytes: bytes, suffix: str) -> str:
    """
    Write uploaded file bytes to a temporary file.

    Args:
        file_bytes: Raw bytes from UploadFile.read().
        suffix:     File extension, e.g. ".mp4" or ".jpg".

    Returns:
        Absolute path to the temporary file.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(file_bytes)
        tmp.flush()
        return tmp.name
    finally:
        tmp.close()


def save_heatmap(heatmap_bgr) -> str:
    """
    Save a Grad-CAM heatmap overlay to the outputs directory.

    Args:
        heatmap_bgr: BGR numpy array (OpenCV format).

    Returns:
        Relative URL path, e.g. '/outputs/heatmap_abc123.png'.
    """
    import cv2
    filename = f"heatmap_{uuid.uuid4().hex[:12]}.png"
    path = os.path.join(OUTPUTS_DIR, filename)
    cv2.imwrite(path, heatmap_bgr)
    logger.debug(f"[FileHandler] Saved heatmap to {path}")
    return f"/outputs/{filename}"


def cleanup_temp(path: str) -> None:
    """Delete a temporary file, silently ignoring errors."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning(f"[FileHandler] Could not delete temp file {path}: {e}")

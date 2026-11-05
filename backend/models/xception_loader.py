"""
Xception Model Loader (Singleton)
===================================
Loads xception_best.pth and caches the XceptionClassifier for the process.

Weight loading:
  1. The checkpoint uses 'backbone.' prefix from the XceptionDetector wrapper.
  2. Strip the prefix → load into XceptionEncoder weights.
  3. pointwise conv fix: unsqueeze(-1)(-1) if dim==2.
  4. strict=False load (adjust_channel keys will be missing, which is expected
     since we're loading into the 'original' mode path).
"""
import logging

import torch

from config import XCEPTION_WEIGHT_PATH, DEVICE
from models.xception_classifier import XceptionClassifier

logger = logging.getLogger(__name__)

_xception_model: XceptionClassifier | None = None


def load_xception() -> XceptionClassifier:
    """
    Load the standalone Xception classifier from disk.
    Cached as process-level singleton; safe to call multiple times.
    """
    global _xception_model
    if _xception_model is not None:
        return _xception_model

    logger.info(f"[XceptionLoader] Loading weights from: {XCEPTION_WEIGHT_PATH}")

    model = XceptionClassifier(num_classes=2)

    checkpoint = torch.load(XCEPTION_WEIGHT_PATH, map_location="cpu")
    if isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            raw = checkpoint["state_dict"]
        elif "model" in checkpoint:
            raw = checkpoint["model"]
        else:
            raw = checkpoint
    else:
        raw = checkpoint

    # Strip 'backbone.' prefix added by XceptionDetector wrapper
    stripped: dict = {}
    for k, v in raw.items():
        new_key = k[len("backbone."):] if k.startswith("backbone.") else k
        # Fix pointwise conv weight shape mismatch
        if "pointwise" in new_key and v.dim() == 2:
            v = v.unsqueeze(-1).unsqueeze(-1)
        stripped[new_key] = v

    missing, unexpected = model.backbone.load_state_dict(stripped, strict=False)
    logger.info(f"[XceptionLoader] Missing keys : {len(missing)}")
    logger.info(f"[XceptionLoader] Unexpected keys: {len(unexpected)}")
    if missing:
        logger.debug(f"[XceptionLoader] Sample missing: {missing[:5]}")

    model.to(DEVICE)
    model.eval()
    _xception_model = model
    logger.info("[XceptionLoader] ✅ Xception classifier loaded and ready.")
    return _xception_model


def get_xception() -> XceptionClassifier:
    """Return cached model. Raises if not yet loaded."""
    if _xception_model is None:
        raise RuntimeError("Xception model not loaded. Call load_xception() at startup.")
    return _xception_model


def xception_predict(tensor: torch.Tensor) -> tuple[float, list[float]]:
    """
    Run Xception inference and return (fake_prob, logits).

    Args:
        tensor: [1, 3, 256, 256], normalized to [-1, 1].

    Returns:
        (fake_prob, [logit_real, logit_fake])
    """
    model = get_xception()
    tensor = tensor.to(DEVICE)
    with torch.no_grad():
        logits, _ = model(tensor)
        probs = torch.softmax(logits, dim=1)
        fake_prob = probs[0, 1].item()
        logit_list = [round(v, 4) for v in logits[0].tolist()]
    return fake_prob, logit_list

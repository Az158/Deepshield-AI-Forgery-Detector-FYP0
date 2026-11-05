"""
Model Loader (Singleton)
=========================
Loads the UCF model ONCE at application startup and exposes predict_tensor().

Weight loading mirrors the original build_backbone() in DeepFakeBench:
  1. Load checkpoint (supports 'state_dict', 'model', or raw dict)
  2. Fix pointwise conv weights (unsqueeze -1 -1)
  3. Strict=False load to handle head keys that differ
"""
import logging

import torch

from config import UCF_WEIGHT_PATH, DEVICE, UCF_BACKBONE_CONFIG
from models.ucf_model import UCFModel

logger = logging.getLogger(__name__)

_model: UCFModel | None = None


def load_model() -> UCFModel:
    """
    Load the UCF model from disk and cache it as a module-level singleton.
    Called once during FastAPI lifespan startup.
    """
    global _model
    if _model is not None:
        return _model

    logger.info(f"[ModelLoader] Loading UCF weights from: {UCF_WEIGHT_PATH}")
    logger.info(f"[ModelLoader] Device: {DEVICE}")

    # Instantiate architecture
    model = UCFModel(
        encoder_feat_dim=UCF_BACKBONE_CONFIG["encoder_feat_dim"],
        num_classes=UCF_BACKBONE_CONFIG["num_classes"],
        num_forgery_types=5,   # FF-DF, FF-F2F, FF-FS, FF-NT + 1
    )

    # Load checkpoint ─ mirrors DeepFakeBench build_backbone()
    checkpoint = torch.load(UCF_WEIGHT_PATH, map_location="cpu")
    if isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        elif "model" in checkpoint:
            state_dict = checkpoint["model"]
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    # Fix pointwise conv weight shape mismatch (DeepFakeBench original fix)
    fixed_state_dict = {}
    for name, weights in state_dict.items():
        if "pointwise" in name and weights.dim() == 2:
            weights = weights.unsqueeze(-1).unsqueeze(-1)
        fixed_state_dict[name] = weights

    # Exclude final linear head to allow partial loads
    fixed_state_dict = {k: v for k, v in fixed_state_dict.items() if "last_linear.weight" not in k
                        and "last_linear.bias" not in k}

    missing, unexpected = model.load_state_dict(fixed_state_dict, strict=False)
    logger.info(f"[ModelLoader] Missing keys : {len(missing)}")
    logger.info(f"[ModelLoader] Unexpected keys: {len(unexpected)}")
    if missing:
        logger.debug(f"[ModelLoader] Sample missing: {missing[:5]}")

    model.to(DEVICE)
    model.eval()
    _model = model
    logger.info("[ModelLoader] ✅ UCF model loaded and ready.")
    return _model


def get_model() -> UCFModel:
    """Return the cached model. Raises if not yet loaded."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() at startup.")
    return _model


def predict_tensor(tensor: torch.Tensor) -> float:
    """
    Run inference on a preprocessed input tensor.

    Args:
        tensor: shape [1, 3, 256, 256], normalized to [-1, 1].

    Returns:
        Fake probability (float in [0, 1]).
    """
    model = get_model()
    tensor = tensor.to(DEVICE)
    return model.predict_prob(tensor)

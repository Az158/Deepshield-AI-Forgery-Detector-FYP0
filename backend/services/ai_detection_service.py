"""
AI Image Detection Service — v2.1 (trained + heuristic fallback)
=================================================================
Detects AI-generated (GAN/diffusion) content.

Priority:
  1. Trained EfficientNet-B0 classifier (ai_classifier.pth) — if available
  2. Classical signal heuristic (FFT-free, min-region-smoothness) — fallback

The trained model is the FYP-2 target. The heuristic runs until the weights
file is placed in backend/weights/ai_classifier.pth.

Integration contract (non-breaking):
  - Single entry point: predict_ai_prob(image_input) -> float [0, 1]
  - Existing pipelines (inference_service, video_service) are UNCHANGED
  - UCF / Xception flows are completely unaffected
  - ai_prob is still an EXTENSION signal; it only overrides the primary label
    if ai_prob >= AI_DETECTION_THRESHOLD (core/decision_logic.py)

Preprocessing note:
  Trained model  → ImageNet mean/std (torchvision standard)
  Heuristic      → raw uint8 RGB or DeepShield tensor (no separate norm needed)
"""
import logging

import cv2
import numpy as np
import torch

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Trained model path (available via local weights OR Hugging Face auto-download)
# ─────────────────────────────────────────────────────────────────────────────

def _predict_trained(image_input) -> float | None:
    """
    Run the trained AI classifier (either custom local or Hugging Face pretrained).

    Returns:
        ai_prob float if trained model is loaded,
        None    if model not yet available (triggers heuristic fallback).
    """
    try:
        from models.ai_classifier_loader import get_ai_classifier, get_ai_model_type, AI_CLASSIFIER_TRANSFORM
        from config import DEVICE

        model = get_ai_classifier()
        model_type = get_ai_model_type()
        
        if model is None or model_type is None:
            return None          # weights/hf absent → fall through to heuristic

        # Convert input to uint8 RGB numpy for standard processing
        if isinstance(image_input, torch.Tensor):
            t = image_input.squeeze(0).permute(1, 2, 0).cpu().numpy()
            rgb_numpy = ((t * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)
        else:
            rgb_numpy = image_input   # already uint8 RGB numpy

        if model_type == "custom_efficientnet":
            # Custom EfficientNet expects ImageNet-normalized tensor
            tensor = AI_CLASSIFIER_TRANSFORM(rgb_numpy).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits = model(tensor)
                ai_prob = torch.softmax(logits, dim=1)[0, 1].item()
                
        elif model_type == "huggingface_vit":
            # Hugging Face pipeline expects numpy array -> PIL Image internal conversion
            ai_prob = model.predict_prob(rgb_numpy)
            
        else:
            return None  # Unknown model type, fallback
            
        logger.info(f"[AIDetect/Trained ({model_type})] ai_prob={ai_prob:.4f}")
        return float(ai_prob)

    except Exception as exc:
        logger.error(f"[AIDetect/Trained] Inference failed: {exc}", exc_info=True)
        return None   # always fall back to heuristic on error


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic fallback (min-region smoothness + median smoothness + noise)
# ─────────────────────────────────────────────────────────────────────────────

def _to_grayscale_numpy(tensor_or_np) -> np.ndarray:
    """Float32 [H,W] in [0,1] from tensor [1,3,H,W] or uint8 RGB numpy."""
    if isinstance(tensor_or_np, torch.Tensor):
        t = tensor_or_np.squeeze(0).permute(1, 2, 0).cpu().numpy()
        t = (t * 0.5 + 0.5).clip(0, 1)
        gray = 0.299 * t[:, :, 0] + 0.587 * t[:, :, 1] + 0.114 * t[:, :, 2]
    else:
        gray_uint8 = cv2.cvtColor(tensor_or_np, cv2.COLOR_RGB2GRAY)
        gray = gray_uint8.astype(np.float32) / 255.0
    return gray.astype(np.float32)


def _min_region_smoothness_score(gray: np.ndarray) -> float:
    """5th-percentile patch variance — detects 'plastic skin' smoothness."""
    h, w = gray.shape
    patch_size = 8
    variances = []
    for y in range(0, h - patch_size, patch_size):
        for x in range(0, w - patch_size, patch_size):
            variances.append(float(np.var(gray[y:y + patch_size, x:x + patch_size])))
    if not variances:
        return 0.5
    p5_var = float(np.percentile(variances, 5))
    score = float(np.clip(1.0 - (p5_var / 0.001), 0.0, 1.0))
    logger.debug(f"[AIDetect/Heuristic] min_region={score:.4f} p5={p5_var:.6f}")
    return score


def _smoothness_score(gray: np.ndarray) -> float:
    """Median patch variance — overall image smoothness."""
    h, w = gray.shape
    patch_size = 8
    variances = []
    for y in range(0, h - patch_size, patch_size):
        for x in range(0, w - patch_size, patch_size):
            variances.append(float(np.var(gray[y:y + patch_size, x:x + patch_size])))
    if not variances:
        return 0.5
    median_var = float(np.median(variances))
    score = float(np.clip(1.0 - (median_var / 0.003), 0.0, 1.0))
    logger.debug(f"[AIDetect/Heuristic] smoothness={score:.4f} median={median_var:.6f}")
    return score


def _noise_score(gray: np.ndarray) -> float:
    """Residual noise uniformity — uniform noise = more AI-like."""
    blurred  = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = gray.astype(np.float32) - blurred.astype(np.float32)
    noise_std = float(np.std(residual))
    patch_vars = [
        float(np.var(residual[y:y+16, x:x+16]))
        for y in range(0, gray.shape[0] - 16, 16)
        for x in range(0, gray.shape[1] - 16, 16)
    ]
    noise_var_of_var = float(np.std(patch_vars)) if len(patch_vars) > 1 else 0.0
    std_score        = float(np.clip(1.0 - (noise_std / 0.025), 0.0, 1.0))
    uniformity_score = float(np.clip(1.0 - (noise_var_of_var / 0.0005), 0.0, 1.0))
    score = 0.5 * std_score + 0.5 * uniformity_score
    logger.debug(f"[AIDetect/Heuristic] noise={score:.4f}")
    return score


def _predict_heuristic(image_input) -> float:
    """Classical signal heuristic (always available, less accurate)."""
    try:
        gray = _to_grayscale_numpy(image_input)
        min_region = _min_region_smoothness_score(gray)
        smooth     = _smoothness_score(gray)
        noise      = _noise_score(gray)
        ai_prob = float(np.clip(0.40 * min_region + 0.35 * smooth + 0.25 * noise, 0.0, 1.0))
        logger.info(
            f"[AIDetect/Heuristic] min_region={min_region:.4f} "
            f"smooth={smooth:.4f} noise={noise:.4f} ai_prob={ai_prob:.4f}"
        )
        return ai_prob
    except Exception as exc:
        logger.error(f"[AIDetect/Heuristic] Failed: {exc}", exc_info=True)
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Public API — single call, automatic routing
# ─────────────────────────────────────────────────────────────────────────────

def predict_ai_prob(image_input) -> float:
    """
    Compute AI-generation probability. Single public entry point.

    Routes to:
      → Trained EfficientNet-B0 if ai_classifier.pth is in backend/weights/
      → Heuristic fallback otherwise (automatic, no config change needed)

    Args:
        image_input: torch.Tensor [1,3,H,W] normalized to [-1,1]
                     OR numpy.ndarray [H,W,3] uint8 RGB

    Returns:
        ai_prob: float in [0, 1].
            >= AI_DETECTION_THRESHOLD (decision_logic.py) → "AI-Generated" override.
    """
    # Try trained model first
    result = _predict_trained(image_input)
    if result is not None:
        return result

    # Fall back to heuristic
    logger.info("[AIDetect] Using heuristic (no trained model loaded)")
    return _predict_heuristic(image_input)

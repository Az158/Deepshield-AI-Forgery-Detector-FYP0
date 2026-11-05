"""
Image Inference Service — v2.1
================================
Uses UCF as the primary model for all images (consistent with FYP-1 findings).
Xception is NOT called for image inference — it is a video-only support signal.

Pipeline:
  preprocess_image
    → UCF inference → deepfake_prob (primary decision authority)
    → AI detection  → ai_prob (extension signal)
    → get_decision_band(deepfake_prob) → forensic band
    → classify(deepfake_prob) → primary label
    → apply_ai_override(label, ai_prob) → final label
    → Grad-CAM++ on UCF.encoder_f.block12
"""
import logging

import torch

from models.model_loader import get_model
from utils.preprocessing import preprocess_image
from core.decision_logic import classify, get_decision_band, apply_ai_override
from core.logging import log_inference
from services.explainability_service import ExplainabilityEngine
from services.ai_detection_service import predict_ai_prob
from config import REAL_THRESHOLD, FAKE_THRESHOLD, DEVICE

logger = logging.getLogger(__name__)

# Lazy-initialised Grad-CAM++ engine targeting UCF.encoder_f.block12
_ucf_explainer: ExplainabilityEngine | None = None


def _get_ucf_explainer() -> ExplainabilityEngine:
    """Return (or create) Grad-CAM++ engine hooked on UCF encoder_f.block12."""
    global _ucf_explainer
    if _ucf_explainer is None:
        model = get_model()
        target_layer = model.encoder_f.block12
        _ucf_explainer = ExplainabilityEngine(model, target_layer=target_layer)
    return _ucf_explainer


def _ucf_inference(tensor: torch.Tensor) -> tuple[float, list[float]]:
    """
    Run UCF inference and return (fake_prob, logits).
    Logs raw logits explicitly.
    """
    model = get_model()
    tensor = tensor.to(DEVICE)
    with torch.no_grad():
        out_sha, _ = model(tensor)
        probs      = torch.softmax(out_sha, dim=1)
        fake_prob  = probs[0, 1].item()
        logit_list = [round(v, 4) for v in out_sha[0].tolist()]

    logger.info(
        f"[InferenceService/UCF] logits={logit_list} | "
        f"prob_real={round(1-fake_prob, 4)} | prob_fake={round(fake_prob, 4)}"
    )
    return fake_prob, logit_list


def analyze_image(image_bytes: bytes) -> dict:
    """
    Full image analysis pipeline (v2.1).

    Steps:
      1. Preprocess: face-detect, crop, 256×256, normalize to [-1,1], RGB
      2. UCF inference → deepfake_prob (PRIMARY)
      3. AI detection → ai_prob (extension signal)
      4. Forensic band + primary label + AI override
      5. Grad-CAM++ on UCF.encoder_f.block12
      6. Log all signals

    Returns:
        Result dict matching the v2.1 /analyze response schema.
    """
    # 1. Preprocess
    tensor, face_crop_rgb, full_image_rgb, bbox = preprocess_image(image_bytes)

    # 2. UCF inference (primary decision)
    deepfake_prob, logits = _ucf_inference(tensor)

    # 3. AI detection (extension)
    ai_prob = predict_ai_prob(face_crop_rgb)

    # 4. Multi-band + primary + override
    band         = get_decision_band(deepfake_prob)
    primary_label = classify(deepfake_prob)
    final_label   = apply_ai_override(primary_label, ai_prob)

    # 5. Log all signals
    logger.info(
        f"[InferenceService] deepfake_prob={deepfake_prob:.4f} | "
        f"ai_prob={ai_prob:.4f} | band={band!r} | "
        f"primary_label={primary_label!r} | final_label={final_label!r}"
    )
    log_inference(
        logger,
        input_type="image",
        raw_prob=deepfake_prob,
        real_threshold=REAL_THRESHOLD,
        fake_threshold=FAKE_THRESHOLD,
        classification=final_label,
    )

    # 6. Grad-CAM++ on UCF.encoder_f.block12
    heatmap_url = ""
    try:
        explainer = _get_ucf_explainer()
        heatmap_url = explainer.generate_heatmap(
            tensor.clone(), 
            full_image_rgb, 
            bbox=bbox,
            method="gradcam++",
            force_zero=(final_label == "Authentic")
        )
    except Exception as exc:
        logger.error(
            f"[InferenceService] Grad-CAM++ FAILED: {exc}", exc_info=True
        )

    return {
        "prediction": final_label,
        "confidence": round(deepfake_prob, 6),
        "band": band,
        "type": "image",
        "heatmap_url": heatmap_url,
        "thresholds": {
            "real": REAL_THRESHOLD,
            "fake": FAKE_THRESHOLD,
        },
        "details": {
            "model": "ucf",
            "ucf_prob": round(deepfake_prob, 6),
            "ai_prob": round(ai_prob, 4),
            "raw_logits": logits,
            "frame_count": None,
            "aggregation_method": None,
        },
    }

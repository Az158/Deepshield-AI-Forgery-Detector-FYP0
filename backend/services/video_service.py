"""
Video Inference Service — v2.1 Dual-Model with UCF Dominance
=============================================================
FYP-1 Context:
  UCF demonstrated strong probability separation on video:
    Real: ~0.45–0.60, Fake: ~0.80–0.95
  UCF is the PRIMARY decision authority.
  Xception provides a per-frame refinement signal only.

Model Roles:
  UCF       → PRIMARY temporal classifier (dominant weight in fusion)
  Xception  → SUPPORT per-frame spatial signal (secondary)

Pipeline:
  1. Extract ≤32 frames (uniform sampling)
  2. Xception per-frame inference → per_frame_probs
  3. UCF temporal inference → ucf_prob
  4. UCF-dominant fusion (decision_logic.fuse_video_probs)
  5. FYP-1 hybrid rule → override to "Manipulated" if triggered
  6. Multi-band + primary label + AI override (on peak frame)
  7. Grad-CAM++ on peak Xception frame (Xception used for Grad-CAM only)
"""
import logging
import tempfile
import os

import cv2
import numpy as np
import torch

from models.xception_loader import get_xception
from models.model_loader import get_model
from utils.preprocessing import preprocess_frame
from core.decision_logic import (
    classify, get_decision_band, fuse_video_probs,
    apply_ai_override, apply_video_hybrid_rule
)
from core.logging import log_inference
from services.ai_detection_service import predict_ai_prob
from config import MAX_VIDEO_FRAMES, REAL_THRESHOLD, FAKE_THRESHOLD, DEVICE

logger = logging.getLogger(__name__)


def _extract_frames_uniform(video_path: str, max_frames: int) -> list[np.ndarray]:
    """
    Extract up to max_frames frames via uniform step sampling.
    Mirrors DeepFakeBench abstract_dataset.py L225-226.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total == 0:
        cap.release()
        raise ValueError("Video has no frames.")

    n_frames = min(max_frames, total)
    step = max(1, total // n_frames)
    indices = [i * step for i in range(n_frames)]

    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    logger.info(
        f"[VideoService] Extracted {len(frames)}/{total} frames "
        f"(step={step}, max={max_frames})"
    )
    return frames


def analyze_video(video_bytes: bytes) -> dict:
    """
    Full v2.1 dual-model video analysis with UCF-dominant fusion.
    """
    suffix = ".mp4"
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        # ── Step 1: Frame extraction ─────────────────────────────────────────
        frames = _extract_frames_uniform(tmp_path, MAX_VIDEO_FRAMES)
        if not frames:
            raise ValueError("No frames could be extracted from the video.")

        frame_count = len(frames)

        # ── Step 2: Xception per-frame inference (support signal) ────────────
        xception_model  = get_xception()
        per_frame_probs: list[float] = []
        tensors:         list[torch.Tensor] = []
        rgb_frames:      list[np.ndarray] = []

        for i, frame in enumerate(frames):
            try:
                tensor = preprocess_frame(frame)
                tensors.append(tensor)
                rgb_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                with torch.no_grad():
                    logits, _ = xception_model(tensor.to(DEVICE))
                    p = torch.softmax(logits, dim=1)
                    fake_prob  = p[0, 1].item()
                    logit_list = [round(v, 4) for v in logits[0].tolist()]

                per_frame_probs.append(fake_prob)
                logger.debug(
                    f"[VideoService/Xception] Frame {i:02d} | "
                    f"logits={logit_list} | fake={fake_prob:.4f}"
                )
            except Exception as e:
                logger.warning(f"[VideoService] Frame {i} skipped: {e}")

        if not per_frame_probs:
            raise ValueError("All frames failed Xception inference.")

        xception_max_prob  = float(np.max(per_frame_probs))
        xception_mean_prob = float(np.mean(per_frame_probs))
        peak_idx           = int(np.argmax(per_frame_probs))
        # fhigh = fraction of frames with prob >= 0.80 (FYP-1 hybrid rule)
        fhigh = float(np.mean([p >= 0.80 for p in per_frame_probs]))

        logger.info(
            f"[VideoService/Xception] "
            f"max={xception_max_prob:.4f} | mean={xception_mean_prob:.4f} | "
            f"fhigh={fhigh:.3f} | peak_frame={peak_idx}"
        )

        # ── Step 3: UCF temporal inference (PRIMARY) ─────────────────────────
        ucf_model = get_model()
        ucf_frame_probs: list[float] = []
        ucf_logits_last: list[float] = []

        for i, t in enumerate(tensors):
            try:
                with torch.no_grad():
                    out, _ = ucf_model(t.to(DEVICE))
                    p_ucf  = torch.softmax(out, dim=1)
                    ucf_frame_probs.append(p_ucf[0, 1].item())
                    ucf_logits_last = [round(v, 4) for v in out[0].tolist()]
            except Exception as e:
                logger.warning(f"[VideoService/UCF] Frame {i} skipped: {e}")

        if ucf_frame_probs:
            ucf_prob = float(np.mean(ucf_frame_probs))
            logger.info(
                f"[VideoService/UCF] ucf_prob={ucf_prob:.4f} "
                f"(mean over {len(ucf_frame_probs)} frames) | "
                f"last_logits={ucf_logits_last}"
            )
        else:
            logger.error("[VideoService/UCF] All UCF frames failed — using Xception mean as fallback.")
            ucf_prob = xception_mean_prob

        # ── Step 4: UCF-dominant fusion ───────────────────────────────────────
        final_prob, w_ucf, w_xc = fuse_video_probs(
            xception_max_prob=xception_max_prob,
            xception_mean_prob=xception_mean_prob,
            ucf_prob=ucf_prob,
        )

        logger.info(
            f"[VideoService/Fusion] "
            f"ucf_prob={ucf_prob:.4f} | xception_max={xception_max_prob:.4f} | "
            f"w_ucf={w_ucf:.4f} | w_xc={w_xc:.4f} | "
            f"final_prob={final_prob:.4f}"
        )

        # ── Step 5: FYP-1 hybrid rule (applied on UCF fraction-weighted data) ─
        hybrid_label = apply_video_hybrid_rule(
            mean_prob=float(np.mean(ucf_frame_probs)) if ucf_frame_probs else xception_mean_prob,
            max_prob=float(np.max(ucf_frame_probs)) if ucf_frame_probs else xception_max_prob,
            fhigh=fhigh,
        )

        # ── Step 6: Band + primary label + AI detection on peak frame ─────────
        band          = get_decision_band(final_prob)
        primary_label = hybrid_label if hybrid_label is not None else classify(final_prob)

        # AI detection on peak Xception frame
        ai_prob = predict_ai_prob(rgb_frames[peak_idx]) if rgb_frames else 0.0

        final_label = apply_ai_override(primary_label, ai_prob)

        # ── Logging ───────────────────────────────────────────────────────────
        logger.info(
            f"[VideoService] final_prob={final_prob:.4f} | band={band!r} | "
            f"hybrid_label={hybrid_label!r} | ai_prob={ai_prob:.4f} | "
            f"final_label={final_label!r}"
        )
        log_inference(
            logger,
            input_type="video",
            raw_prob=final_prob,
            real_threshold=REAL_THRESHOLD,
            fake_threshold=FAKE_THRESHOLD,
            classification=final_label,
            frame_count=frame_count,
        )

        # ── Step 7: Grad-CAM++ on peak Xception frame ─────────────────────────
        heatmap_url = ""
        try:
            from services.explainability_service import ExplainabilityEngine
            target_layer = xception_model.get_block12()
            explainer    = ExplainabilityEngine(xception_model, target_layer=target_layer)
            heatmap_url  = explainer.generate_heatmap(
                tensors[peak_idx], rgb_frames[peak_idx], method="gradcam++"
            )
            logger.info(
                f"[VideoService] Grad-CAM++ on peak frame {peak_idx} "
                f"(xception_fake={per_frame_probs[peak_idx]:.4f}) → {heatmap_url}"
            )
        except Exception as cam_err:
            logger.error(
                f"[VideoService] Grad-CAM++ FAILED: {cam_err}", exc_info=True
            )

        # ── Return ────────────────────────────────────────────────────────────
        return {
            "prediction": final_label,
            "confidence": round(final_prob, 6),
            "band": band,
            "type": "video",
            "heatmap_url": heatmap_url,
            "thresholds": {
                "real": REAL_THRESHOLD,
                "fake": FAKE_THRESHOLD,
            },
            "details": {
                "frame_count": frame_count,
                "aggregation_method": "ucf_dominant_fusion",
                "ucf_prob": round(ucf_prob, 6),
                "xception_max": round(xception_max_prob, 6),
                "xception_mean": round(xception_mean_prob, 6),
                "ai_prob": round(ai_prob, 4),
                "fusion_weights": {
                    "ucf": w_ucf,
                    "xception": w_xc,
                },
                "hybrid_rule_fired": hybrid_label is not None,
                "peak_frame_index": peak_idx,
                "peak_frame_prob": round(per_frame_probs[peak_idx], 6),
                "per_frame_probs": [round(p, 6) for p in per_frame_probs],
            },
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

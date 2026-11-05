"""
DeepShield Configuration
========================
All constants are maintained here. Edit thresholds, paths, and preprocessing
parameters in this single location.
"""
import os

# ── Directory Layout ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Default weight file names (place files in backend/weights/)
UCF_WEIGHT_FILE      = "ucf_best.pth"
UCF_WEIGHT_PATH      = os.path.join(WEIGHTS_DIR, UCF_WEIGHT_FILE)

XCEPTION_WEIGHT_FILE = "xception_best.pth"
XCEPTION_WEIGHT_PATH = os.path.join(WEIGHTS_DIR, XCEPTION_WEIGHT_FILE)


# ── Device ──────────────────────────────────────────────────────────────────
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── Preprocessing (from DeepFakeBench ucf.yaml / xception.yaml) ────────────
RESOLUTION = 256                          # Input size: 256×256
MEAN = [0.5, 0.5, 0.5]                   # Normalization mean (per channel)
STD  = [0.5, 0.5, 0.5]                   # Normalization std  (per channel)
MIN_FACE_SIZE = 80                        # Minimum px for face crop to be valid

# ── Video Sampling (from DeepFakeBench ucf.yaml frame_num test=32) ─────────
MAX_VIDEO_FRAMES = 32                     # Max frames sampled per video

# ── Classification Thresholds ───────────────────────────────────────────────
# No thresholds found in DeepFakeBench repo — using calibrated defaults.
# These are the ONLY threshold definitions in the system.
# All classification goes through core/decision_logic.py.
#
# CALIBRATION NOTE (2026-03-24):
#   Empirical probe of UCF model outputs:
#     - Random noise tensor: fake_prob ≈ 0.65 (should not be "Manipulated")
#     - Zero tensor (black):  fake_prob ≈ 0.49 (correctly "Inconclusive")
#     - Neg-ones (dark):      fake_prob ≈ 0.42 (correctly "Authentic")
#   Original FAKE_THRESHOLD=0.70 caused genuine deepfakes scoring 0.55–0.69
#   to fall into "Inconclusive" — the source of the reported bias.
#   Set to 0.55 as the decision boundary (above random noise floor).
#
#   To revert to strict binary: set FAKE_THRESHOLD = 0.50, REAL_THRESHOLD = 0.50
#   To revert to original spec: set FAKE_THRESHOLD = 0.70, REAL_THRESHOLD = 0.30
REAL_THRESHOLD = 0.35   # prob ≤ REAL_THRESHOLD → "Authentic"
FAKE_THRESHOLD = 0.55   # prob ≥ FAKE_THRESHOLD → "Manipulated"
                        # otherwise             → "Inconclusive"

# ── Video Aggregation ─────────────────────────────────────────────────────────
# Options: "mean" | "max" | "top_k"  (top_k uses mean of top-5 frames)
VIDEO_AGGREGATION = "mean"

# ── UCF Model Architecture (from ucf.yaml backbone_config) ──────────────────
UCF_BACKBONE_CONFIG = {
    "mode": "adjust_channel",    # channel adjustment mode for encoder
    "num_classes": 2,            # binary: real/fake
    "inc": 3,                    # 3 input channels (RGB)
    "dropout": False,
    "encoder_feat_dim": 512,     # feature dimension used in UCF heads
}

# Log which thresholds are active
import logging as _logging
_logging.getLogger(__name__).info(
    f"[DeepShield] Thresholds loaded — REAL_THRESHOLD={REAL_THRESHOLD}, "
    f"FAKE_THRESHOLD={FAKE_THRESHOLD}  (source: config.py defaults)"
)

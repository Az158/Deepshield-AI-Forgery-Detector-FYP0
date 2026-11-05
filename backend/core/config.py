# ============================================================
# FILE: core/config.py
# TASK(S): Task 1 (Code Sanitization), Task 3 (No Heatmap for Real Images)
# CHANGES:
#   - Created core/config.py to consolidate all configuration.
#   - Added all specific constants requested in Task 1.
#   - Added config validation function to check weight files.
#   - Added HEATMAP_MIN_CONFIDENCE = 0.55 for Task 3.
# ============================================================
"""
DeepShield Configuration
========================
All constants are maintained here. Edit thresholds, paths, and preprocessing
parameters in this single location.
"""
import os

# ── Directory Layout ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Default weight file paths
UCF_WEIGHTS_PATH      = os.path.join(WEIGHTS_DIR, "ucf_best.pth")
XCEPTION_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "xception_best.pth")
AI_CLASSIFIER_PATH    = os.path.join(WEIGHTS_DIR, "ai_classifier.pth")

# ── Device ──────────────────────────────────────────────────────────────────
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── Preprocessing ───────────────────────────────────────────────────────────
RESOLUTION = 256                          # Legacy resolution identifier
INPUT_SIZE = 256                          # Input size: 256x256
MEAN = [0.5, 0.5, 0.5]                   # Normalization mean (per channel)
STD  = [0.5, 0.5, 0.5]                   # Normalization std  (per channel)
MIN_FACE_SIZE = 30                        # Minimum face crop size

# ── Video Sampling ──────────────────────────────────────────────────────────
VIDEO_FRAME_COUNT = 8                     # Max frames sampled per video

# ── Classification Thresholds ───────────────────────────────────────────────
REAL_THRESHOLD = 0.35   # prob <= REAL_THRESHOLD -> "Authentic"
FAKE_THRESHOLD = 0.55   # prob >= FAKE_THRESHOLD -> "Manipulated"

# AI override
AI_DETECTION_THRESHOLD = 0.55

# ── Video Fusion Metrics Thresholds ─────────────────────────────────────────
FHIGH_THRESHOLD = 0.80

# FYP-1 Hybrid Decision Rule variables
HYBRID_MEAN_THRESHOLD = 0.70
HYBRID_SPIKE_MEAN = 0.55
HYBRID_SPIKE_MAX = 0.90
HYBRID_SPIKE_FHIGH = 0.10

# ── Heatmap Configuration ───────────────────────────────────────────────────
HEATMAP_MIN_CONFIDENCE = 0.55

# ── Allowed Extension & Constraints ─────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi"}
MAX_FILE_SIZE_MB = 50

# ── UCF Model Architecture ──────────────────────────────────────────────────
UCF_BACKBONE_CONFIG = {
    "mode": "adjust_channel",    # channel adjustment mode for encoder
    "num_classes": 2,            # binary: real/fake
    "inc": 3,                    # 3 input channels (RGB)
    "dropout": False,
    "encoder_feat_dim": 512,     # feature dimension used in UCF heads
}

def validate_config():
    """Validates that required weight files exist at startup."""
    if not os.path.exists(UCF_WEIGHTS_PATH):
        raise RuntimeError(f"UCF weights not found at {UCF_WEIGHTS_PATH}")
    if not os.path.exists(XCEPTION_WEIGHTS_PATH):
        raise RuntimeError(f"Xception weights not found at {XCEPTION_WEIGHTS_PATH}")

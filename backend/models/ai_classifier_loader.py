"""
AI Classifier Loader (Singleton)
==================================
Loads an AI Image Classifier once at startup.

Priority:
  1. Local Custom Weights: backend/weights/ai_classifier.pth
     (If you trained your own EfficientNet-B0 model)
  2. Hugging Face Pretrained: umm-maybe/AI-image-detector
     (Auto-downloads weights if 'transformers' is installed)
  3. Heuristic Fallback:
     (If neither is available, returns None and system falls back to signals)

This ensures the server never fails to start, but seamlessly upgrades to
trained AI detection when weights/dependencies are present.
"""
import logging
import os

import torch
from torchvision import transforms

from config import DEVICE, WEIGHTS_DIR
from models.ai_classifier import AIImageClassifier
from models.hf_ai_classifier import HuggingFaceAIClassifier, TRANSFORMERS_AVAILABLE

logger = logging.getLogger(__name__)

AI_CLASSIFIER_PATH = os.path.join(WEIGHTS_DIR, "ai_classifier.pth")

# Used ONLY for the local custom AIImageClassifier (priority 1)
AI_CLASSIFIER_TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

_ai_model = None
_model_type = None  # Track which type of model was loaded


def load_ai_classifier():
    """
    Load the trained AI classifier. Cached as singleton.

    Returns:
        Loaded model (Custom or HuggingFace), or None if unavailable.
    """
    global _ai_model, _model_type

    if _ai_model is not None:
        return _ai_model

    # Priority 1: Local Custom Weights
    if os.path.exists(AI_CLASSIFIER_PATH):
        logger.info(f"[AIClassifierLoader] Found local weights at {AI_CLASSIFIER_PATH}")
        try:
            model = AIImageClassifier(pretrained=False)
            state = torch.load(AI_CLASSIFIER_PATH, map_location="cpu")
            model.load_state_dict(state)
            model.to(DEVICE).eval()
            _ai_model = model
            _model_type = "custom_efficientnet"
            logger.info("[AIClassifierLoader] Local custom AI classifier loaded.")
            return _ai_model
        except Exception as e:
            logger.error(f"[AIClassifierLoader] Failed to load local custom weights: {e}")

    # Priority 2: Hugging Face Pretrained
    if TRANSFORMERS_AVAILABLE:
        logger.info("[AIClassifierLoader] Local weights not found. Attempting Hugging Face pretrained model...")
        try:
            model = HuggingFaceAIClassifier(device=DEVICE)
            _ai_model = model
            _model_type = "huggingface_vit"
            logger.info("[AIClassifierLoader] Hugging Face pretrained AI classifier loaded.")
            return _ai_model
        except Exception as e:
            logger.error(f"[AIClassifierLoader] Failed to load Hugging Face model: {e}")

    # Priority 3: Fallback
    logger.warning(
        "[AIClassifierLoader] No trained AI models available (no local weights + "
        "transformers not installed or failed). Using heuristic fallback."
    )
    return None


def get_ai_classifier():
    """Return cached model (None if not loaded / weights absent)."""
    return _ai_model


def get_ai_model_type():
    """Return the type of model loaded: 'custom_efficientnet', 'huggingface_vit', or None."""
    return _model_type

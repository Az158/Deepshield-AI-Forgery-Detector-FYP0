"""
Hugging Face AI Classifier Wrapper
====================================
Downloads and wraps a pretrained AI image detection model from Hugging Face.
Model used: umm-maybe/AI-image-detector (ViT-based, highly accurate).
"""
import logging
from typing import Any

import numpy as np
import torch
from PIL import Image

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Hugging Face model repository
HF_MODEL_ID = "umm-maybe/AI-image-detector"


class HuggingFaceAIClassifier:
    """Wrapper for the Hugging Face AI image detector pipeline."""

    def __init__(self, device: str):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "The 'transformers' library is required to use the Hugging Face model. "
                "Install it with: pip install transformers"
            )

        # Device mapping for transformers pipeline
        pipe_device = 0 if "cuda" in str(device) else -1
        
        logger.info(f"[HFAICLassifier] Initializing Hugging Face pipeline for '{HF_MODEL_ID}'...")
        # This will auto-download weights on the first run and cache them locally (~340MB)
        self.pipe = pipeline("image-classification", model=HF_MODEL_ID, device=pipe_device)
        logger.info("[HFAICLassifier] Pipeline ready.")

    def predict_prob(self, rgb_numpy: np.ndarray) -> float:
        """
        Run inference and return the probability of the image being AI-generated.
        
        Args:
            rgb_numpy: [H, W, 3] uint8 RGB array.
            
        Returns:
            ai_prob: float in [0, 1]
        """
        # The pipeline expects a PIL Image
        pil_img = Image.fromarray(rgb_numpy)
        
        # Pipeline output format:
        # [{'label': 'artificial', 'score': 0.9}, {'label': 'human', 'score': 0.1}]
        results = self.pipe(pil_img)
        
        # Extract the 'artificial' score
        ai_prob = 0.0
        for res in results:
            if res["label"].lower() == "artificial":
                ai_prob = float(res["score"])
                break
                
        return ai_prob

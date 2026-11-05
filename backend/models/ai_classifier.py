"""
AI Image Classifier (Trained)
================================
EfficientNet-B0 fine-tuned for AI-generated vs real image detection.

Architecture:
  EfficientNet-B0 backbone (ImageNet pretrained)
  + custom head: Dropout(0.3) → Linear(1280, 2)
  
  Output: [B, 2] logits
    Index 0 = Real
    Index 1 = AI-Generated

Preprocessing for this model (DIFFERENT from UCF/Xception):
  - Resize 256×256
  - Normalize with ImageNet statistics:
    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
  
  Do NOT use the DeepShield [-1,1] normalization for this model.

Training details: see assets/training/train_ai_classifier.py
Expected accuracy: ~90–95% on ArtiFact test set.
"""
import torch
import torch.nn as nn
import torchvision.models as tv_models


class AIImageClassifier(nn.Module):
    """
    Lightweight EfficientNet-B0 AI/real binary classifier.
    Drop-in replacement for the heuristic ai_detection_service.
    """

    def __init__(self, pretrained: bool = False):
        """
        Args:
            pretrained: Load ImageNet weights (True during training only).
                        During inference, weights come from ai_classifier.pth.
        """
        super().__init__()
        weights = tv_models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        self.backbone = tv_models.efficientnet_b0(weights=weights)

        # Replace the default classifier head
        in_features = self.backbone.classifier[1].in_features  # 1280
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, 3, 256, 256] — ImageNet normalized
        Returns:
            logits: [B, 2]
        """
        return self.backbone(x)

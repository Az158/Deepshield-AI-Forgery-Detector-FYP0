"""
Standalone Xception Classifier
================================
Wraps the existing XceptionEncoder backbone with a standalone classifier
that uses the 2048-dim global pooling path (NOT the UCF adjust_channel path).

This matches xception.yaml:
  backbone_config:
    mode: original      ← 2048 → last_linear(2), NOT adjust_channel
    num_classes: 2
    inc: 3
    dropout: false

Checkpoint format (xception_best.pth):
  Keys prefixed with 'backbone.' from the XceptionDetector wrapper.
  Stripped to fit XceptionEncoder.

Target layer for Grad-CAM++: block12 (last spatial 1024-channel conv block).
"""
import logging

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.xception import XceptionEncoder

logger = logging.getLogger(__name__)


class XceptionClassifier(nn.Module):
    """
    Standalone Xception classifier using the 'original' (2048-d) path.

    Input:  [B, 3, 256, 256], normalized to [-1, 1], RGB.
    Output: (logits [B, 2], features [B, 1024, H, W]) from block12.

    Architecture:
      Entry flow (conv1–block3) → Middle flow (block4–11) →
      Exit flow part-1 (block12) → conv3/bn3 → conv4/bn4 →
      relu → AdaptiveAvgPool(1) → flatten → last_linear → [B, 2]

    Grad-CAM++ hooks into block12 (spatial, 1024-ch, 8×8 at 256 input).
    """

    def __init__(self, num_classes: int = 2):
        super().__init__()
        self.backbone = XceptionEncoder(num_classes=num_classes, dropout=False)

    def get_block12(self) -> nn.Module:
        """Expose block12 as Grad-CAM++ target layer."""
        return self.backbone.block12

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass using the ORIGINAL (2048-d) Xception path.

        Returns:
            logits:    [B, 2]          — binary real/fake logits
            block12_out: [B, 1024, H, W] — spatial activation for Grad-CAM++
        """
        # --- Entry flow ---
        x = self.backbone.fea_part1(x)   # [B, 64, 127, 127]
        x = self.backbone.fea_part2(x)   # [B, 728, 16, 16]
        x = self.backbone.fea_part3(x)   # [B, 728, 16, 16]

        # --- Exit flow part 1 (block12) — target for Grad-CAM++ ---
        x = self.backbone.fea_part4(x)   # block8-12 → [B, 1024, 8, 8]
        block12_out = x                   # HOOK TARGET

        # --- Exit flow part 2 ---
        x = self.backbone.relu(self.backbone.bn3(self.backbone.conv3(x)))
        x = self.backbone.bn4(self.backbone.conv4(x))
        x = self.backbone.relu(x)        # [B, 2048, 8, 8]

        # --- Global average pool → classify ---
        x = F.adaptive_avg_pool2d(x, (1, 1))
        x = x.view(x.size(0), -1)        # [B, 2048]
        logits = self.backbone.last_linear(x)  # [B, 2]

        return logits, block12_out

    def predict_prob(self, x: torch.Tensor) -> float:
        """
        Run inference and return fake probability (scalar).
        MUST be called outside torch.no_grad() for Grad-CAM++ compatibility.
        """
        logits, _ = self.forward(x)
        return torch.softmax(logits, dim=1)[0, 1].item()

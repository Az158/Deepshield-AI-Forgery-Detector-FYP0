"""
Standalone UCF Model
=====================
Extracted from DeepFakeBench/training/detectors/ucf_detector.py.
All training infrastructure (loss, metrics, registry) removed.
Only inference-relevant code preserved.

Reference:
  Yan et al., "UCF: Uncovering Common Features for Generalizable Deepfake
  Detection", arXiv 2304.13949, 2023.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from models.xception import XceptionEncoder


# ── Sub-modules (UCF-specific, from ucf_detector.py) ────────────────────────

class AdaIN(nn.Module):
    """Adaptive Instance Normalization used in Conditional U-Net."""
    def __init__(self, eps: float = 1e-5):
        super().__init__()
        self.eps = eps

    def _c_norm(self, x, bs, ch, eps=1e-7):
        x_var = x.var(dim=-1) + eps
        x_std = x_var.sqrt().view(bs, ch, 1, 1)
        x_mean = x.mean(dim=-1).view(bs, ch, 1, 1)
        return x_std, x_mean

    def forward(self, x, y):
        size = x.size()
        bs, ch = size[:2]
        x_ = x.view(bs, ch, -1)
        y_ = y.reshape(bs, ch, -1)
        x_std, x_mean = self._c_norm(x_, bs, ch, eps=self.eps)
        y_std, y_mean = self._c_norm(y_, bs, ch, eps=self.eps)
        return ((x - x_mean.expand(size)) / x_std.expand(size)) \
               * y_std.expand(size) + y_mean.expand(size)


def _r_double_conv(in_ch, out_ch):
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.ReLU(inplace=True),
        nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.ReLU(inplace=True),
    )


class Conditional_UNet(nn.Module):
    """Content reconstruction decoder (used only during training, kept for weight compatibility)."""
    def __init__(self):
        super().__init__()
        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.maxpool = nn.MaxPool2d(2)
        self.dropout = nn.Dropout(p=0.3)
        self.adain3 = AdaIN()
        self.adain2 = AdaIN()
        self.adain1 = AdaIN()
        self.dconv_up3 = _r_double_conv(512, 256)
        self.dconv_up2 = _r_double_conv(256, 128)
        self.dconv_up1 = _r_double_conv(128, 64)
        self.conv_last = nn.Conv2d(64, 3, 1)
        self.up_last = nn.Upsample(scale_factor=4, mode='bilinear', align_corners=True)
        self.activation = nn.Tanh()

    def forward(self, c, x):
        x = self.adain3(x, c)
        x = self.upsample(x); x = self.dropout(x); x = self.dconv_up3(x)
        c = self.upsample(c); c = self.dropout(c); c = self.dconv_up3(c)
        x = self.adain2(x, c)
        x = self.upsample(x); x = self.dropout(x); x = self.dconv_up2(x)
        c = self.upsample(c); c = self.dropout(c); c = self.dconv_up2(c)
        x = self.adain1(x, c)
        x = self.upsample(x); x = self.dropout(x); x = self.dconv_up1(x)
        x = self.conv_last(x)
        return self.activation(self.up_last(x))


class Head(nn.Module):
    """Classification head with dropout + 2-layer MLP."""
    def __init__(self, in_f: int, hidden_dim: int, out_f: int):
        super().__init__()
        self.do = nn.Dropout(0.2)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.mlp = nn.Sequential(
            nn.Linear(in_f, hidden_dim),
            nn.LeakyReLU(inplace=True),
            nn.Linear(hidden_dim, out_f),
        )

    def forward(self, x):
        bs = x.size(0)
        feat = self.pool(x).view(bs, -1)
        out = self.mlp(feat)
        out = self.do(out)
        return out, feat


class Conv2d1x1(nn.Module):
    """1×1 conv feature splitter (block_spe / block_sha)."""
    def __init__(self, in_f: int, hidden_dim: int, out_f: int):
        super().__init__()
        self.conv2d = nn.Sequential(
            nn.Conv2d(in_f, hidden_dim, 1, 1), nn.LeakyReLU(inplace=True),
            nn.Conv2d(hidden_dim, hidden_dim, 1, 1), nn.LeakyReLU(inplace=True),
            nn.Conv2d(hidden_dim, out_f, 1, 1),
        )

    def forward(self, x):
        return self.conv2d(x)


# ── UCF Detector Model ───────────────────────────────────────────────────────

class UCFModel(nn.Module):
    """
    UCF dual-encoder deepfake detector (inference-only version).

    Architecture (from ucf.yaml + ucf_detector.py):
      encoder_f & encoder_c: Xception in adjust_channel mode (512-ch output)
      block_spe, block_sha:  Conv2d1x1 splitters (512→256 each)
      head_sha:              Head(256, 512, 2) — used for real/fake prediction
      head_spe:              Head(256, 512, N_forgeries) — not used in inference
      con_gan:               Conditional_UNet — not used in inference

    Inference flow:
      x → encoder_f → forgery_features
        → block_sha → head_sha → softmax[:, 1] → fake probability
    """

    def __init__(self, encoder_feat_dim: int = 512, num_classes: int = 2,
                 num_forgery_types: int = 5):
        super().__init__()
        half_dim = encoder_feat_dim // 2  # 256

        # Two identical Xception encoders (forgery + content)
        self.encoder_f = XceptionEncoder(num_classes=num_classes)
        self.encoder_c = XceptionEncoder(num_classes=num_classes)

        # Reconstruction U-Net (weight compatibility only)
        self.con_gan = Conditional_UNet()

        # Feature splitters
        self.block_spe = Conv2d1x1(encoder_feat_dim, half_dim, half_dim)
        self.block_sha = Conv2d1x1(encoder_feat_dim, half_dim, half_dim)

        # Classification heads
        # head_sha: real/fake head (num_classes=2)
        self.head_sha = Head(in_f=half_dim, hidden_dim=encoder_feat_dim, out_f=num_classes)
        # head_spe: forgery-type head (num_forgery_types = len(train_datasets)+1 = 5)
        self.head_spe = Head(in_f=half_dim, hidden_dim=encoder_feat_dim, out_f=num_forgery_types)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Inference forward pass.

        Returns:
            out_sha: logits [B, 2]
            sha_feat: pooled feature vector [B, 256]
        """
        # Feature extraction via forgery encoder
        forgery_features = self.encoder_f.features(x)  # [B, 512, H', W']

        # Split into specific/shared branches
        f_sha = self.block_sha(forgery_features)        # [B, 256, H', W']

        # Classify via shared head (real/fake)
        out_sha, sha_feat = self.head_sha(f_sha)        # [B, 2], [B, 256]
        return out_sha, sha_feat

    def predict_prob(self, x: torch.Tensor) -> float:
        """
        Run inference on a pre-processed batch tensor and return fake probability.

        Args:
            x: tensor of shape [1, 3, 256, 256], already normalized.

        Returns:
            Scalar float in [0, 1] — probability the input is manipulated.
        """
        with torch.no_grad():
            out_sha, _ = self.forward(x)
            prob = torch.softmax(out_sha, dim=1)[0, 1].item()
        return prob

"""
Standalone Xception Network
============================
Extracted verbatim from DeepFakeBench/training/networks/xception.py.
All DETECTOR/BACKBONE registry wiring removed so this can be imported
standalone without the DeepFakeBench package structure.

Original source:
  https://github.com/ondyari/FaceForensics/blob/master/classification/network/xception.py
  Modified by Zhiyuan Yan (DeepFakeBench)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class SeparableConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1,
                 padding=0, dilation=1, bias=False):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_channels, in_channels, kernel_size,
            stride, padding, dilation, groups=in_channels, bias=bias
        )
        self.pointwise = nn.Conv2d(in_channels, out_channels, 1, 1, 0, 1, 1, bias=bias)

    def forward(self, x):
        x = self.conv1(x)
        x = self.pointwise(x)
        return x


class Block(nn.Module):
    def __init__(self, in_filters, out_filters, reps, strides=1,
                 start_with_relu=True, grow_first=True):
        super().__init__()
        if out_filters != in_filters or strides != 1:
            self.skip = nn.Conv2d(in_filters, out_filters, 1, stride=strides, bias=False)
            self.skipbn = nn.BatchNorm2d(out_filters)
        else:
            self.skip = None

        self.relu = nn.ReLU(inplace=True)
        rep = []
        filters = in_filters

        if grow_first:
            rep.append(self.relu)
            rep.append(SeparableConv2d(in_filters, out_filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(out_filters))
            filters = out_filters

        for _ in range(reps - 1):
            rep.append(self.relu)
            rep.append(SeparableConv2d(filters, filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(filters))

        if not grow_first:
            rep.append(self.relu)
            rep.append(SeparableConv2d(in_filters, out_filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(out_filters))

        if not start_with_relu:
            rep = rep[1:]
        else:
            rep[0] = nn.ReLU(inplace=False)

        if strides != 1:
            rep.append(nn.MaxPool2d(3, strides, 1))

        self.rep = nn.Sequential(*rep)

    def forward(self, inp):
        x = self.rep(inp)
        if self.skip is not None:
            skip = self.skip(inp)
            skip = self.skipbn(skip)
        else:
            skip = inp
        x += skip
        return x


class XceptionEncoder(nn.Module):
    """
    Xception backbone in 'adjust_channel' mode as used by UCF detector.

    Architecture:
      Entry flow:  conv1→bn1→relu, conv2→bn2→relu, block1–3
      Middle flow: block4–11
      Exit flow:   block12, conv3/bn3/relu, conv4/bn4
      Channel adj: 2048 → 512 via 1×1 conv (used by UCF)

    Output of features(): feature map [B, 512, H', W']
    """

    def __init__(self, num_classes: int = 2, dropout: bool = False):
        super().__init__()
        # Entry flow
        self.conv1 = nn.Conv2d(3, 32, 3, 2, 0, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(32, 64, 3, bias=False)
        self.bn2 = nn.BatchNorm2d(64)

        self.block1  = Block(64,  128,  2, 2, start_with_relu=False, grow_first=True)
        self.block2  = Block(128, 256,  2, 2, start_with_relu=True,  grow_first=True)
        self.block3  = Block(256, 728,  2, 2, start_with_relu=True,  grow_first=True)
        # Middle flow
        self.block4  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block5  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block6  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block7  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block8  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block9  = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block10 = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        self.block11 = Block(728, 728,  3, 1, start_with_relu=True,  grow_first=True)
        # Exit flow
        self.block12 = Block(728, 1024, 2, 2, start_with_relu=True,  grow_first=False)
        self.conv3 = SeparableConv2d(1024, 1536, 3, 1, 1)
        self.bn3 = nn.BatchNorm2d(1536)
        self.conv4 = SeparableConv2d(1536, 2048, 3, 1, 1)
        self.bn4 = nn.BatchNorm2d(2048)

        # Classifier head (used when running plain Xception, not UCF)
        if dropout:
            self.last_linear = nn.Sequential(
                nn.Dropout(p=dropout),
                nn.Linear(2048, num_classes)
            )
        else:
            self.last_linear = nn.Linear(2048, num_classes)

        # UCF channel-adjustment path: 2048 → 512
        self.adjust_channel = nn.Sequential(
            nn.Conv2d(2048, 512, 1, 1, 0),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=False),
        )

    # ── named sub-pass helpers (mirror DeepFakeBench naming) ────────────────

    def fea_part1(self, x):
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        return x

    def fea_part2(self, x):
        return self.block3(self.block2(self.block1(x)))

    def fea_part3(self, x):
        return self.block7(self.block6(self.block5(self.block4(x))))

    def fea_part4(self, x):
        return self.block12(self.block11(self.block10(self.block9(self.block8(x)))))

    def fea_part5(self, x):
        x = self.relu(self.bn3(self.conv3(x)))
        x = self.bn4(self.conv4(x))
        return x

    def features(self, x) -> torch.Tensor:
        """Return 512-channel feature map (adjust_channel mode)."""
        x = self.fea_part1(x)
        x = self.fea_part2(x)
        x = self.fea_part3(x)
        x = self.fea_part4(x)
        x = self.fea_part5(x)
        x = self.adjust_channel(x)
        return x

    def classifier(self, features: torch.Tensor) -> torch.Tensor:
        x = self.relu(features)
        x = F.adaptive_avg_pool2d(x, (1, 1))
        x = x.view(x.size(0), -1)
        return self.last_linear(x)

    def forward(self, x):
        feats = self.features(x)
        out = self.classifier(feats)
        return out, feats

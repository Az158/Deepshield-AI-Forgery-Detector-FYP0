"""
Explainability Service — Grad-CAM++ (Primary) with Grad-CAM Fallback
======================================================================
Implements Grad-CAM++ (Chattopadhay et al., 2018) as the primary method.
Falls back to standard Grad-CAM if Grad-CAM++ fails.

Target layer: encoder_f.block12 — the last spatial convolutional block of
XceptionEncoder, immediately before the exit-flow conv3/conv4. At resolution
256×256 input this produces spatial maps of size [B, 1024, 8, 8].

CRITICAL GRADIENT NOTES:
  - Do NOT use torch.no_grad() during CAM generation.
  - Do NOT call .detach() on activations/gradients before use.
  - The activation hook must preserve requires_grad so backprop flows.
  - We use retain_graph=False (single backward call per image).

API:
    engine = ExplainabilityEngine(model)
    url = engine.generate_heatmap(tensor, original_rgb, method="gradcam++")
"""
import logging
from typing import Optional, Literal

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from utils.file_handler import save_heatmap

logger = logging.getLogger(__name__)

Method = Literal["gradcam++", "gradcam"]


class ExplainabilityEngine:
    """
    Class-activation mapping engine supporting Grad-CAM++ and Grad-CAM.

    Args:
        model:        UCFModel (or any PyTorch model that produces [B,2] logits).
        target_layer: nn.Module to hook (default: model.encoder_f.block12).
                      Must be a spatial conv layer with a >1×1 output.
    """

    def __init__(self, model, target_layer=None):
        self.model = model

        if target_layer is None:
            # Last spatial block in the Xception exit flow — 1024 channels, 8×8 at 256 input
            self.target_layer = model.encoder_f.block12
        else:
            self.target_layer = target_layer

        # State captured by hooks — NOT pre-detached
        self._activations: Optional[torch.Tensor] = None
        self._gradients: Optional[torch.Tensor] = None
        self._hooks: list = []

    # ── Hook Management ──────────────────────────────────────────────────────

    def _register_hooks(self) -> None:
        """
        Register forward and backward hooks.

        IMPORTANT: activations are stored WITHOUT .detach() so that gradients
        can flow through them for higher-order gradient computation (Grad-CAM++).
        The raw tensor is kept alive until _remove_hooks() is called.
        """

        def _fwd_hook(_module, _input, output):
            # Store without detach — we need grad to flow for Grad-CAM++
            self._activations = output

        def _bwd_hook(_module, _grad_input, grad_output):
            # grad_output[0] ∈ R^[B, C, H, W] — gradient w.r.t. activations
            # detach here since we only need the numeric values post-backward
            self._gradients = grad_output[0].detach()

        self._hooks = [
            self.target_layer.register_forward_hook(_fwd_hook),
            self.target_layer.register_full_backward_hook(_bwd_hook),
        ]

    def _remove_hooks(self) -> None:
        for h in self._hooks:
            h.remove()
        self._hooks = []
        self._activations = None
        self._gradients = None

    # ── Grad-CAM++ ───────────────────────────────────────────────────────────

    def _compute_gradcam_plus_plus(self) -> np.ndarray:
        """
        Grad-CAM++ as per Chattopadhay et al., 2018.
        https://arxiv.org/abs/1710.11063

        Algorithm:
          1. A   = forward activations  [1, C, H, W]
          2. g   = dScore/dA             [1, C, H, W]   (from backward hook)
          3. g²  = g * g
          4. g³  = g * g²
          5. α_c_k  = g² / (2*g² + A·sum(g³) + eps)     [1, C, H, W]
             (second-order gradient weighting term)
          6. w_k = sum_{i,j}(α_c_k * ReLU(g))_ij        [1, C, 1, 1]
          7. CAM = ReLU(sum_k(w_k * A_k))               [H, W]
          8. Normalize to [0, 1]
        """
        A = self._activations  # [1, C, H, W] — still has grad_fn
        g = self._gradients    # [1, C, H, W] — detached numeric values

        # Work with detached activation values for the alpha computation
        A_val = A.detach()

        eps = 1e-7
        g2 = g * g                          # [1, C, H, W]
        g3 = g * g2                         # [1, C, H, W]

        # sum(g³) over spatial dims
        sum_g3 = g3.sum(dim=(2, 3), keepdim=True)   # [1, C, 1, 1]

        # Alpha weights (Eq. 7 in the paper)
        alpha = g2 / (2.0 * g2 + A_val * sum_g3 + eps)  # [1, C, H, W]

        # Importance weight per channel: α weighted by ReLU(g)
        # sum over spatial dims
        w = (alpha * F.relu(g)).sum(dim=(2, 3), keepdim=True)  # [1, C, 1, 1]

        # Weighted combination of activation maps
        cam = (w * A_val).sum(dim=1, keepdim=True)   # [1, 1, H, W]
        cam = F.relu(cam)

        return self._normalize_cam(cam)

    # ── Grad-CAM (fallback) ──────────────────────────────────────────────────

    def _compute_gradcam(self) -> np.ndarray:
        """
        Standard Grad-CAM (Selvaraju et al., 2017).
        Used as fallback if Grad-CAM++ fails.
        """
        A = self._activations.detach()  # [1, C, H, W]
        g = self._gradients             # [1, C, H, W]

        # Global average pool of gradients → channel weights
        w = g.mean(dim=(2, 3), keepdim=True)   # [1, C, 1, 1]
        cam = (w * A).sum(dim=1, keepdim=True)  # [1, 1, H, W]
        cam = F.relu(cam)

        return self._normalize_cam(cam)

    # ── Shared Utilities ─────────────────────────────────────────────────────

    @staticmethod
    def _normalize_cam(cam: torch.Tensor) -> np.ndarray:
        """Normalize a CAM tensor to float32 numpy array in [0, 1]."""
        cam_np = cam.squeeze().cpu().numpy().astype(np.float32)
        c_min, c_max = cam_np.min(), cam_np.max()
        if c_max - c_min > 1e-8:
            cam_np = (cam_np - c_min) / (c_max - c_min)
        else:
            cam_np = np.zeros_like(cam_np)
        return cam_np

    @staticmethod
    def _overlay(cam_np: np.ndarray, original_rgb: np.ndarray, bbox: tuple[int, int, int, int] | None = None) -> np.ndarray:
        """Resize CAM and create a colourised overlay exactly mapping to the face."""
        original_h, original_w = original_rgb.shape[:2]
        full_cam = np.zeros((original_h, original_w), dtype=np.float32)
        
        # Step 5: CRITICAL — resize CAM to EXACT face bounding box
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            bw, bh = x2 - x1, y2 - y1
            cam_resized = cv2.resize(cam_np, (bw, bh), interpolation=cv2.INTER_LINEAR)
            full_cam[y1:y2, x1:x2] = cam_resized
        else:
            full_cam = cv2.resize(cam_np, (original_w, original_h), interpolation=cv2.INTER_LINEAR)
        
        # Step 6: Apply colormap to full-resolution CAM
        heatmap_uint8 = np.uint8(255 * full_cam)
        heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        heatmap_rgb = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
        
        # Step 7: Overlay on ORIGINAL image
        original_float = original_rgb.astype(np.float32)
        heatmap_float = heatmap_rgb.astype(np.float32)
        overlay = np.uint8(
            np.clip(0.6 * original_float + 0.4 * heatmap_float, 0, 255)
        )
        
        # Return BGR for cv2.imwrite
        result_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
        return result_bgr

    # ── Public API ───────────────────────────────────────────────────────────

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        original_rgb: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
        method: Method = "gradcam++",
        class_idx: int = 1,
        force_zero: bool = False,
    ) -> str:
        """
        Generate a Grad-CAM++ (or Grad-CAM) heatmap overlay and persist it.

        Args:
            input_tensor: [1, 3, 256, 256] pre-processed model input.
            original_rgb: uint8 RGB numpy array used for visual overlay.
            method:       'gradcam++' (default) or 'gradcam' (fallback).
            class_idx:    Target class index. 1 = fake/manipulated.

        Returns:
            Relative URL of the saved PNG, e.g. '/outputs/heatmap_xxx.png'.
            Returns '' if generation fails after all fallbacks.
        """
        try:
            # ── Forward + Backward with gradient tape ──────────────────────
            self._register_hooks()
            self.model.eval()

            # CRITICAL: do NOT use torch.no_grad() here — we need gradients
            tensor = input_tensor.clone().requires_grad_(True)

            out_sha, _ = self.model(tensor)     # [1, 2] logits
            score = out_sha[0, class_idx]       # scalar: fake-class score

            logger.debug(
                f"[Explainability] Forward done. "
                f"logits={[round(v,4) for v in out_sha[0].detach().tolist()]} "
                f"target_score={score.item():.4f}"
            )

            self.model.zero_grad()
            score.backward()                    # populates self._gradients via hook

            if self._gradients is None or self._activations is None:
                raise RuntimeError("Hooks did not capture activations/gradients.")

            logger.debug(
                f"[Explainability] Gradients shape: {self._gradients.shape}, "
                f"Activations shape: {self._activations.shape}"
            )

            # ── Compute CAM ────────────────────────────────────────────────
            used_method = method
            if method == "gradcam++":
                try:
                    cam_np = self._compute_gradcam_plus_plus()
                    logger.info(f"[Explainability] Grad-CAM++ computed. Max={cam_np.max():.4f}")
                except Exception as gpp_err:
                    logger.warning(
                        f"[Explainability] Grad-CAM++ failed ({gpp_err}), "
                        f"falling back to Grad-CAM"
                    )
                    cam_np = self._compute_gradcam()
                    used_method = "gradcam"
            else:
                cam_np = self._compute_gradcam()

            if force_zero:
                cam_np = np.zeros_like(cam_np) if 'cam_np' in locals() else np.zeros((8, 8), dtype=np.float32)

            # ── Overlay and save ───────────────────────────────────────────
            overlay = self._overlay(cam_np, original_rgb, bbox)
            url = save_heatmap(overlay)
            original_h, original_w = original_rgb.shape[:2]
            logger.info(
                f"[Explainability] {used_method.upper()} heatmap saved {url} ({original_w}x{original_h})"
            )
            return url

        except Exception as exc:
            logger.error(
                f"[Explainability] Heatmap generation FAILED: {exc}",
                exc_info=True
            )
            return ""
        finally:
            self._remove_hooks()

    # ── Convenience alias (backward-compatible with old generate() callers) ──
    def generate(self, tensor: torch.Tensor, original_rgb: np.ndarray) -> str:
        """Backward-compatible wrapper — delegates to generate_heatmap."""
        return self.generate_heatmap(tensor, original_rgb, method="gradcam++")

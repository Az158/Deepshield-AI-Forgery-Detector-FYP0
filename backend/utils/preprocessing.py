"""
Preprocessing Utilities
========================
Mirrors the DeepFakeBench abstract_dataset.py preprocessing exactly:
  1. cv2.imdecode → BGR array
  2. cv2.cvtColor(BGR→RGB)
  3. Face detection and crop (Haar cascade)
  4. cv2.resize to RESOLUTION×RESOLUTION using INTER_CUBIC
  5. ToTensor() → [0,1] float
  6. Normalize(mean=[0.5,0.5,0.5], std=[0.5,0.5,0.5]) → [-1,1]
  7. Unsqueeze(0) → [1, 3, H, W]
"""
import cv2
import numpy as np
import torch
import torchvision.transforms as T

from config import RESOLUTION, MEAN, STD, MIN_FACE_SIZE

# ── Face detector (Haar cascade) ────────────────────────────────────────────
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

_normalize = T.Normalize(mean=MEAN, std=STD)
_to_tensor = T.ToTensor()


# ── Core helpers ─────────────────────────────────────────────────────────────

def _detect_and_crop(bgr_img: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """
    Detect the largest face in an image and return a padded RGB crop.
    Falls back to full image if no face is detected.

    Padding factor 1.5× mimics the dlib-based face extraction used in
    DeepFakeBench preprocessing (scale_factor ≈ 1.3–1.5).
    """
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )

    if len(faces) == 0:
        # No face → use the whole image
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        h, w = bgr_img.shape[:2]
        return rgb, (0, 0, w, h)

    # Pick largest face
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = faces[0]

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        raise ValueError(
            f"Detected face too small ({w}×{h}px). "
            f"Minimum required: {MIN_FACE_SIZE}×{MIN_FACE_SIZE}px."
        )

    # Expand bounding box by 1.5× around the face center
    img_h, img_w = bgr_img.shape[:2]
    cx, cy = x + w / 2, y + h / 2
    nw, nh = w * 1.5, h * 1.5
    x1 = max(0, int(cx - nw / 2))
    y1 = max(0, int(cy - nh / 2))
    x2 = min(img_w, int(cx + nw / 2))
    y2 = min(img_h, int(cy + nh / 2))

    crop_bgr = bgr_img[y1:y2, x1:x2]
    return cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB), (x1, y1, x2, y2)


def _apply_transform(rgb_np: np.ndarray) -> torch.Tensor:
    """
    Resize → ToTensor → Normalize.
    Mirrors abstract_dataset.py lines 313–316, 402–405.
    """
    resized = cv2.resize(rgb_np, (RESOLUTION, RESOLUTION), interpolation=cv2.INTER_CUBIC)
    tensor = _to_tensor(resized)           # [3, H, W] float32 in [0, 1]
    tensor = _normalize(tensor)            # [3, H, W] float32 in [-1, 1]
    return tensor.unsqueeze(0)             # [1, 3, H, W]


# ── Public API ───────────────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes) -> tuple[torch.Tensor, np.ndarray, np.ndarray, tuple[int, int, int, int]]:
    """
    Decode, face-crop, resize, and normalize an image.

    Args:
        image_bytes: Raw file bytes (JPEG / PNG / WebP).

    Returns:
        tensor (torch.Tensor)      : [1, 3, 256, 256] input for UCF deepfake model
        face_crop_rgb (np.ndarray) : Face RGB crop for AI model accuracy
        full_image_rgb (np.ndarray): Full RGB image for Grad-CAM overlay
        bbox (tuple)               : Coordinates of the face for routing

    Raises:
        ValueError: If image cannot be decoded or face is too small.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Could not decode image. Ensure it is a valid image file.")

    full_image_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    face_crop_rgb, bbox = _detect_and_crop(bgr)
    tensor = _apply_transform(face_crop_rgb)
    return tensor, face_crop_rgb, full_image_rgb, bbox


def preprocess_frame(bgr_frame: np.ndarray) -> torch.Tensor:
    """
    Preprocess a single video frame (BGR numpy array).

    Args:
        bgr_frame: Frame in BGR format as returned by cv2.VideoCapture.

    Returns:
        tensor — [1, 3, 256, 256] normalized input for the model.
    """
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    return _apply_transform(rgb)

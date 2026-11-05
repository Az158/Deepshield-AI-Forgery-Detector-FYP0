"""Diagnose AI detection scores on different image types."""
import sys, cv2, numpy as np, torch
sys.path.insert(0, r'C:\Users\walee\OneDrive\Desktop\University Work\FYP\V2\backend')
from services.ai_detection_service import _freq_score, _smoothness_score, _noise_score, _to_grayscale_numpy, predict_ai_prob

def test(name, rgb_img):
    gray = _to_grayscale_numpy(rgb_img)
    f = _freq_score(gray)
    s = _smoothness_score(gray)
    n = _noise_score(gray)
    ai = predict_ai_prob(rgb_img)
    print(f"{name:30s} freq={f:.3f} smooth={s:.3f} noise={n:.3f} → ai_prob={ai:.3f}")

# Simulate different image types
np.random.seed(42)

# 1. Random noise (should score LOW — clearly not AI)
test("Random noise",            np.random.randint(0,255,(256,256,3),dtype=np.uint8))

# 2. Solid flat color (should score HIGH — AI-like smooth)
test("Solid gray",              np.full((256,256,3),128,dtype=np.uint8))

# 3. Gaussian blur on noise (smooth but noisy — AI-similar)
base = np.random.randint(50,200,(256,256,3),dtype=np.uint8)
blurred = cv2.GaussianBlur(base,(21,21),0)
test("Blurred noise",           blurred)

# 4. Gradient image (smooth gradient — AI-similar)
x = np.linspace(80,180,256,dtype=np.uint8)
gradient = np.stack([np.tile(x,(256,1))]*3, axis=2)
test("Gradient image",          gradient)

# 5. Portrait-like: smooth center + textured border (AI portrait simulation)
portrait = np.random.randint(180,210,(256,256,3),dtype=np.uint8)  # smooth skin
portrait[:30,:,:] = np.random.randint(0,255,(30,256,3),dtype=np.uint8)   # hair
portrait[-30:,:,:] = np.random.randint(0,255,(30,256,3),dtype=np.uint8)
portrait = cv2.GaussianBlur(portrait,(3,3),0)
test("Portrait-like (AI sim)", portrait)

# 6. Natural photo sim: full texture throughout
natural = np.random.randint(0,255,(256,256,3),dtype=np.uint8)
natural = cv2.GaussianBlur(natural,(3,3),0)
test("Natural texture sim",     natural)

# 7. Very smooth face-like
smooth_face = np.zeros((256,256,3),dtype=np.uint8)
smooth_face[:,:] = [190, 165, 145]  # skin tone
smooth_face = cv2.GaussianBlur(smooth_face,(15,15),0) + np.random.randint(0,3,(256,256,3),dtype=np.uint8)
test("Very smooth face",        smooth_face.astype(np.uint8))

print()
print("=== Raw smoothness thresholds ===")
for base_var in [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.015, 0.02]:
    s = max(0.0, min(1.0, 1.0 - (base_var / 0.015)))
    print(f"  median_var={base_var:.4f} → smooth_score={s:.3f}")

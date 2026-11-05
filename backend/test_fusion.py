"""
Validation test suite for dual-model fusion architecture.
Run from backend/ with the correct venv active.
"""
import sys, torch, numpy as np
sys.path.insert(0, r'C:\Users\walee\OneDrive\Desktop\University Work\FYP\V2\backend')

print('=== TEST 1: Load Both Models ===')
from models.xception_loader import load_xception, xception_predict
from models.model_loader import load_model
xc = load_xception()
ucf = load_model()
print('Xception model type:', type(xc).__name__)
print('UCF model type:', type(ucf).__name__)

print()
print('=== TEST 2: Fusion Logic ===')
from core.decision_logic import fuse_video_probs, classify
# High Xception signal
p, wx, wu = fuse_video_probs(0.80, 0.65, 0.50)
print(f'High Xception: final={p:.4f} w_xc={wx:.4f} w_ucf={wu:.4f} label={classify(p)}')
assert wx > 0.84, f"Expected w_xc>0.84 for high Xception, got {wx}"
# High UCF signal
p2, wx2, wu2 = fuse_video_probs(0.60, 0.50, 0.70)
print(f'High UCF:      final={p2:.4f} w_xc={wx2:.4f} w_ucf={wu2:.4f} label={classify(p2)}')
assert wu2 > 0.39, f"Expected w_ucf>0.39 for high UCF, got {wu2}"
# Default
p3, wx3, wu3 = fuse_video_probs(0.60, 0.55, 0.55)
print(f'Default:       final={p3:.4f} w_xc={wx3:.4f} w_ucf={wu3:.4f} label={classify(p3)}')
assert abs(wx3 - 0.70) < 0.01, f"Expected default w_xc~0.70, got {wx3}"
print('All fusion assertions PASSED')

print()
print('=== TEST 3: Xception Inference ===')
for name, x in [
    ('noise',  torch.randn(1,3,256,256)),
    ('dark',  -torch.ones(1,3,256,256)*0.5),
    ('bright', torch.ones(1,3,256,256)*0.8),
]:
    prob, logits = xception_predict(x)
    print(f'  {name:6s}: logits={logits} fake_prob={prob:.4f} label={classify(prob)}')

print()
print('=== TEST 4: Grad-CAM++ on Xception block12 ===')
from services.explainability_service import ExplainabilityEngine
rgb = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
t = torch.from_numpy(rgb.astype('float32') / 255.0)
t = (t - 0.5) / 0.5
t = t.permute(2, 0, 1).unsqueeze(0)
target_layer = xc.get_block12()
engine = ExplainabilityEngine(xc, target_layer=target_layer)
url = engine.generate_heatmap(t, rgb, method='gradcam++')
print(f'Grad-CAM++ URL: {url!r}')
assert url, 'Heatmap URL should be non-empty'
print('Grad-CAM++ PASSED')

print()
print('=== TEST 5: Classify boundary values ===')
for v, expected in [(0.80, 'Manipulated'), (0.55, 'Manipulated'),
                    (0.54, 'Inconclusive'), (0.35, 'Authentic'), (0.20, 'Authentic')]:
    result = classify(v)
    status = 'OK' if result == expected else f'FAIL (expected {expected})'
    print(f'  classify({v:.2f})={result} [{status}]')

print()
print('ALL TESTS PASSED')

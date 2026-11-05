"""
DeepShield v2.1 Validation Test Suite
"""
import sys, torch, numpy as np
sys.path.insert(0, r'C:\Users\walee\OneDrive\Desktop\University Work\FYP\V2\backend')

print('=== TEST 1: Load Models ===')
from models.model_loader import load_model
from models.xception_loader import load_xception
xc = load_xception()
ucf = load_model()
print(f'Xception: {type(xc).__name__} | UCF: {type(ucf).__name__}')

print()
print('=== TEST 2: Decision Logic Functions ===')
from core.decision_logic import (
    classify, get_decision_band, fuse_video_probs,
    apply_ai_override, apply_video_hybrid_rule
)

# classify()
assert classify(0.80) == 'Manipulated', 'FAIL classify 0.80'
assert classify(0.45) == 'Inconclusive', 'FAIL classify 0.45'
assert classify(0.20) == 'Authentic', 'FAIL classify 0.20'
print('classify() OK')

# get_decision_band()
assert get_decision_band(0.20) == 'Real', f'FAIL band 0.20: {get_decision_band(0.20)}'
assert get_decision_band(0.50) == 'Unsure', f'FAIL band 0.50: {get_decision_band(0.50)}'
assert get_decision_band(0.70) == 'Likely Fake', f'FAIL band 0.70: {get_decision_band(0.70)}'
assert get_decision_band(0.90) == 'Strong Fake', f'FAIL band 0.90: {get_decision_band(0.90)}'
print('get_decision_band() OK')

# apply_ai_override()
assert apply_ai_override('Authentic', 0.80) == 'AI-Generated', 'FAIL ai_override high'
assert apply_ai_override('Authentic', 0.50) == 'AI-Generated', 'FAIL ai_override edge'
assert apply_ai_override('Manipulated', 0.90) == 'Manipulated', 'FAIL ai_override should NOT override Manipulated'
print('apply_ai_override() OK')

# fuse_video_probs() — UCF dominant
prob, w_ucf, w_xc = fuse_video_probs(0.60, 0.50, 0.80)  # high UCF
assert w_ucf > w_xc, f'FAIL: w_ucf ({w_ucf}) should > w_xc ({w_xc}) for high UCF'
assert abs(w_ucf - 0.80) < 0.01, f'FAIL: w_ucf should be ~0.80, got {w_ucf}'
print(f'High UCF:       final={prob:.4f} w_ucf={w_ucf:.4f} w_xc={w_xc:.4f} [OK]')

prob2, w_ucf2, w_xc2 = fuse_video_probs(0.90, 0.70, 0.50)  # high Xception
assert w_ucf2 > w_xc2, f'FAIL: w_ucf ({w_ucf2}) still must > w_xc ({w_xc2}) even for high Xception'
print(f'High Xception:  final={prob2:.4f} w_ucf={w_ucf2:.4f} w_xc={w_xc2:.4f} [OK, UCF still dominant]')

prob3, w_ucf3, w_xc3 = fuse_video_probs(0.60, 0.50, 0.55)  # default
assert abs(w_ucf3 - 0.60) < 0.01, f'FAIL: default w_ucf should be ~0.60, got {w_ucf3}'
print(f'Default:        final={prob3:.4f} w_ucf={w_ucf3:.4f} w_xc={w_xc3:.4f} [OK]')

# hybrid rule
h = apply_video_hybrid_rule(0.75, 0.92, 0.15)
assert h == 'Manipulated', f'FAIL hybrid rule: {h}'
h2 = apply_video_hybrid_rule(0.40, 0.60, 0.05)
assert h2 is None, f'FAIL hybrid rule no-fire: {h2}'
print('apply_video_hybrid_rule() OK')

print()
print('=== TEST 3: AI Detection ===')
from services.ai_detection_service import predict_ai_prob

# Real photo-like (random noise — should score relatively low)
noise_rgb = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
ai_noise = predict_ai_prob(noise_rgb)
print(f'Random noise image ai_prob={ai_noise:.4f}')

# Uniform (very smooth — should score high)
smooth_rgb = np.full((256, 256, 3), 128, dtype=np.uint8)
ai_smooth = predict_ai_prob(smooth_rgb)
print(f'Smooth solid image ai_prob={ai_smooth:.4f} (expect > noise)')
assert ai_smooth > ai_noise, 'FAIL: smooth image should score higher than noise'
print('AI detection ordering OK')

print()
print('=== TEST 4: UCF Inference on Synthetic Inputs ===')
for name, x in [('noise',  torch.randn(1,3,256,256)),
                 ('dark',  -torch.ones(1,3,256,256)*0.5),
                 ('bright', torch.ones(1,3,256,256)*0.8)]:
    with torch.no_grad():
        out, _ = ucf(x)
        p = torch.softmax(out, dim=1)
        fake = round(p[0,1].item(), 4)
    band = get_decision_band(fake)
    label = classify(fake)
    print(f'  {name:6s}: fake={fake:.4f} band={band!r} label={label!r}')

print()
print('=== TEST 5: Grad-CAM++ on UCF.encoder_f.block12 ===')
from services.explainability_service import ExplainabilityEngine
rgb = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
t = torch.from_numpy(rgb.astype('float32') / 255.0)
t = (t - 0.5) / 0.5
t = t.permute(2, 0, 1).unsqueeze(0)
engine = ExplainabilityEngine(ucf, target_layer=ucf.encoder_f.block12)
url = engine.generate_heatmap(t, rgb, method='gradcam++')
assert url, 'FAIL: UCF Grad-CAM++ returned empty URL'
print(f'UCF Grad-CAM++ URL: {url!r} [OK]')

print()
print('ALL v2.1 TESTS PASSED')

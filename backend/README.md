# DeepShield Backend v2.1 🛡️

DeepShield is a state-of-the-art forensic media analysis backend. Built with FastAPI and PyTorch, this system detects both heavily manipulated DeepFake imagery/videos and AI-generated (GAN/Diffusion) content. It leverages advanced dual-encoder Xception networks alongside HuggingFace Vision Transformers to provide strict forensic decision logic.

## 1. Project Overview & Architecture
DeepShield v2.1 serves as the central API backend for media forensics. The system accepts raw image or video bytes, preprocesses them appropriately, and feeds them into two independent parallel pipelines (UCF and Xception) for temporal anomaly and manipulation classification, respectively. An AI-detector extension runs in tandem, overriding primary predictions with "AI-Generated" if its threshold is exceeded. 
Grad-CAM++ heatmaps are automatically produced only for statistically significant manipulation evidence.

## 2. API Endpoints Contract
### `GET /health`
Returns system health, device availability (CPU/CUDA), and loaded model statuses.

### `POST /analyze`
Accepts `Multipart/form-data` with a single file parameter `file`.
**Response Schema**:
```json
{
  "prediction": "Authentic" | "Manipulated" | "Inconclusive" | "AI-Generated",
  "confidence": 0.000000,
  "band": "Real" | "Unsure" | "Likely Fake" | "Strong Fake",
  "type": "image" | "video",
  "heatmap_url": "/outputs/heatmap_UUID_filename.png",
  "heatmap_generated": true | false,
  "thresholds": {
    "real": 0.35,
    "fake": 0.55
  },
  "details": {
    "model": "ucf_only" | "ucf_and_xception",
    "ucf_prob": 0.000000,
    "ai_prob": 0.000000,
    ...
  }
}
```

## 3. Directory Structure
```text
backend/
├── api/             # FastAPI routes
├── app/             # Application initialization
├── blockchain/      # Blockchain anchoring subsystem (FYP-2)
├── core/            # Config, Logger, and Decision Logic
├── models/          # Model architecture and loader wrappers
├── outputs/         # Generated heatmaps and static files
├── reports/         # PDF report generation (FYP-2)
├── services/        # Service layer (inference, video, ai, explainability)
├── utils/           # Preprocessing and file handling
└── weights/         # Pre-trained model `.pth` files
```

## 4. Configuration Requirements
Environment variables or changes inside `core/config.py`:
- `DEVICE`: Auto-detects `cuda` or `cpu`.
- Model paths: `WEIGHTS_DIR` -> `weights/ucf_best.pth`, `xception_best.pth`, `ai_classifier.pth`.

## 5. Decision Thresholds Explained
- `REAL_THRESHOLD` (0.35): Any confidence <= 0.35 is marked "Authentic".
- `FAKE_THRESHOLD` (0.55): Any confidence >= 0.55 is marked "Manipulated".
- Between 0.35 and 0.55 is strictly "Inconclusive".
- `AI_DETECTION_THRESHOLD` (0.55): If AI prob >= 0.55, prediction is overridden to "AI-Generated" without impacting the underlying forensic band.

## 6. Preprocessing
Uses deepfake standard face detection via OpenCV `haarcascade_frontalface_default.xml`, sorted by size (largest area first), with a minimum size of `30x30`. The crop is expanded by 1.5x and resized to `256x256`. 
Grad-CAM++ visualizations strictly overlay back onto the *full original resolution image/frame*.

## 7. Model Inference Logic
Images utilize solely the UCF dual-encoder framework for deepfake probabilities. Videos split paths: Xception executes per-frame inference to find the peak-anomaly frame, while UCF aggregates temporal consistency probabilities.

## 8. Video Fusion Formula
For video context, the combined model framework is UCF-dominant. Formula:
`final_prob = w_ucf * ucf_prob + w_xc * mean_xc`
- Standard: `w_ucf=0.60`, `w_xc=0.40`.
- Strong UCF Signal (`ucf_prob >= 0.75`): `w_ucf=0.80`, `w_xc=0.20`.
- Strong Xception Burst (`max_prob >= 0.85` & `fhigh >= 0.20`): `w_ucf=0.55`, `w_xc=0.45`.

## 9. Grad-CAM++ Implementation specifics
Grad-CAM++ traces gradients specifically back to `block12` of the encoder. It guarantees 1:1 original source overlay dimensions rather than heavily pixelated model tensors, generating heatmaps only when probabilities pass the `0.55` manipulation threshold.

## 10. AI Detector Priority Fallback
1. **Hugging Face ViT**: `umm-maybe/AI-image-detector` using transformers pipeline.
2. **Local Custom Classifier**: `EfficientNet-B0` architecture if `ai_classifier.pth` is available.
3. **Classical Heuristics**: Automatic degradation to Noise uniformity (45%), Edge consistency (35%), and Color correlation (20%).

## 11. Security Measures Applied
- `MAX_FILE_SIZE`: Restricted to `50MB`.
- `ALLOWED_MIME_TYPES`: Whitelisted for `jpeg/png/mp4` exclusively.
- **Filename sanitization**: Strictly replaces illegal characters via strict `basename` stripping.
- **Secure File Serving**: Output directory limits relative path traversal explicitly.

## 12. Logging Standards
DeepShield produces unified struct-like single-line strings at INFO level for metrics scraping.
Format: `[DeepShield][inference] filename={filename} model={details.model} ucf_prob={details.ucf_prob:.4f} ai_prob={details.ai_prob:.4f} prediction={prediction} band={band} time={T}s`

## 13. FYP-1 Video Hybrid Rules
Applies temporal aggregation triggers:
- If `mean_prob` >= `0.55`, flag as Manipulated.
- If `mean_prob` >= `0.45` AND `max_prob` >= `0.85` AND `fhigh` >= `0.20`, flag as Manipulated.

## 14. Temporary File Cleanup Strategy
FastAPI `BackgroundTasks` executes post-response. Upload bytes are held temporarily per-inference utilizing native `tempfile` interfaces before forced unlink calls.

## 15. Stubs and Future Extensions
- `reports/__init__.py`: Scaffold for forensic PDF integration (FYP-2).
- `blockchain/__init__.py`: Scaffold for smart contract metric anchoring (FYP-2).

## 16. Instructions to Run
1. `pip install -r requirements.txt`
2. Download model checkpoints to `/weights/`
3. Execute `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` (Note: workers bound to 1 due to PyTorch singleton constraints).

## 17. PDF Report Dependencies
PDF report generation uses WeasyPrint. Install the required OS libraries before enabling report generation:

- Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2`
- macOS: `brew install pango cairo`
- Windows: install the GTK3 runtime listed in the WeasyPrint documentation.

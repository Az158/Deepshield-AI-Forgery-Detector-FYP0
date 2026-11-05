"""
DeepShield Decision Logic & Fusion — v2.1
==========================================
THIS IS THE ONLY PLACE IN THE CODEBASE WHERE:
  - Thresholds are applied
  - Model output fusion is performed
  - Multi-band classification is produced

FYP-1 Design Context (CRITICAL):
  Experimental results showed UCF produces strong probability separation:
    Real inputs:  ~0.45–0.60
    Fake inputs:  ~0.80–0.95
  Xception was found to produce weak separation (~0.45–0.55), making it
  unsuitable as a primary classifier. UCF is therefore the decision authority.

Model Roles:
  UCF       → PRIMARY decision authority (images + video)
  Xception  → SUPPORT refinement signal only (video only via frame scores)

Classification:
  Primary labels: Manipulated / Inconclusive / Authentic  (for API)
  Forensic bands: Strong Fake / Likely Fake / Unsure / Real  (for interpretability)
  Special label:  AI-Generated (overrides primary when ai_prob ≥ 0.70)
"""
from config import REAL_THRESHOLD, FAKE_THRESHOLD

# ── Fusion weight constants ─────────────────────────────────────────────────
# UCF weight MUST always be >= Xception in default scenarios (FYP-1 constraint)
_W_UCF_BASE      = 0.60
_W_XCEPTION_BASE = 0.40

_HIGH_UCF_THRESHOLD      = 0.75   # Strong UCF signal → UCF even more dominant
_HIGH_XCEPTION_THRESHOLD = 0.85   # Very high Xception peak → slight Xception boost

# ── Band boundaries (FYP-1 forensic interpretation) ─────────────────────────
_BAND_REAL        = 0.30
_BAND_UNSURE_MAX  = 0.65
_BAND_LIKELY_MAX  = 0.85

# ── AI detection threshold ───────────────────────────────────────────────────
# Calibration note (2026-03-24):
#   User AI sample scored ai_prob=0.5443 → missed 0.55 threshold.
#   Real natural photos score ~0.00–0.30 (natural grain in smoothest patches).
#   Lowered to 0.50 — still well above real photo range (0.15).
#   To make stricter (fewer AI-Generated labels): raise toward 0.60.
#   To make more aggressive: lower toward 0.45.
AI_DETECTION_THRESHOLD = 0.50




# ── Primary 3-class label ────────────────────────────────────────────────────

def classify(prob: float) -> str:
    """
    Map fake probability to the primary 3-class label.

    Args:
        prob: softmax fake-class probability in [0, 1].

    Returns:
        "Manipulated"  if prob >= FAKE_THRESHOLD (0.55)
        "Authentic"    if prob <= REAL_THRESHOLD (0.35)
        "Inconclusive" otherwise
    """
    if prob >= FAKE_THRESHOLD:
        return "Manipulated"
    elif prob <= REAL_THRESHOLD:
        return "Authentic"
    else:
        return "Inconclusive"


# ── Multi-band forensic interpretation (FYP-1 system) ────────────────────────

def get_decision_band(prob: float) -> str:
    """
    Map fake probability to a forensic interpretation band.
    Preserves the FYP-1 4-band system exactly.

    Bands:
      Real        → p ≤ 0.30
      Unsure      → 0.30 < p < 0.65
      Likely Fake → 0.65 ≤ p < 0.85
      Strong Fake → p ≥ 0.85
    """
    if prob <= _BAND_REAL:
        return "Real"
    elif prob < _BAND_UNSURE_MAX:
        return "Unsure"
    elif prob < _BAND_LIKELY_MAX:
        return "Likely Fake"
    else:
        return "Strong Fake"


# ── AI-Generated override ────────────────────────────────────────────────────

def apply_ai_override(primary_label: str, ai_prob: float) -> str:
    """
    Override the primary label with "AI-Generated" if ai_prob is high enough,
    EXCEPT when the image is already confidently flagged as "Manipulated".
    The forensic band is NOT affected by this override.

    Args:
        primary_label: Result of classify() or fuse + classify().
        ai_prob:       AI-generation probability from ai_detection_service.

    Returns:
        "AI-Generated" if ai_prob >= AI_DETECTION_THRESHOLD and it's not Manipulated,
        else primary_label unchanged.
    """
    if ai_prob >= AI_DETECTION_THRESHOLD and primary_label != "Manipulated":
        return "AI-Generated"
    return primary_label


# ── UCF-dominant fusion (video only) ─────────────────────────────────────────

def fuse_video_probs(
    xception_max_prob: float,
    xception_mean_prob: float,
    ucf_prob: float,
) -> tuple[float, float, float]:
    """
    UCF-dominant confidence-aware fusion for video classification.

    UCF is the decision authority. Xception is a refinement signal only.

    Weighting rules (priority order):
      1. ucf_prob ≥ 0.75:     Strong UCF signal → W_UCF=0.80, W_XC=0.20
      2. xception_max ≥ 0.85: Very high Xception peak → W_UCF=0.55, W_XC=0.45
      3. Default:             W_UCF=0.60, W_XC=0.40

    Note: UCF weight is NEVER lower than Xception in any scenario.

    Args:
        xception_max_prob:  Highest per-frame Xception fake probability.
        xception_mean_prob: Mean per-frame Xception fake probability (unused in
                            fusion formula but logged for diagnostics).
        ucf_prob:           UCF temporal fake probability.

    Returns:
        (final_prob, w_ucf_normalized, w_xception_normalized)
    """
    # Dynamic weight selection (UCF-dominant)
    if ucf_prob >= _HIGH_UCF_THRESHOLD:
        w_ucf = 0.80
        w_xc  = 0.20
    elif xception_max_prob >= _HIGH_XCEPTION_THRESHOLD:
        w_ucf = 0.55
        w_xc  = 0.45
    else:
        w_ucf = _W_UCF_BASE
        w_xc  = _W_XCEPTION_BASE

    # Normalize
    total = w_ucf + w_xc
    w_ucf_n = w_ucf / total
    w_xc_n  = w_xc  / total

    # UCF-primary fusion formula
    final_prob = (w_ucf_n * ucf_prob) + (w_xc_n * xception_max_prob)

    return round(final_prob, 6), round(w_ucf_n, 4), round(w_xc_n, 4)


# ── FYP-1 video hybrid decision rule ─────────────────────────────────────────

def apply_video_hybrid_rule(
    mean_prob: float,
    max_prob: float,
    fhigh: float,
) -> str | None:
    """
    FYP-1 temporal aggregation hybrid rule for video classification.
    Applied BEFORE multi-band system when clear thresholds are crossed.

    Rules:
      If mean_prob ≥ 0.70 → "Manipulated" (clear majority)
      If mean_prob ≥ 0.55 AND max_prob ≥ 0.90 AND fhigh ≥ 0.10 → "Manipulated"
      Else → None (fall through to band/classify system)

    Args:
        mean_prob: Mean per-frame fake probability.
        max_prob:  Max per-frame fake probability.
        fhigh:     Fraction of frames with prob ≥ 0.80.

    Returns:
        "Manipulated" if rule fires, else None.
    """
    if mean_prob >= 0.70:
        return "Manipulated"
    if mean_prob >= 0.55 and max_prob >= 0.90 and fhigh >= 0.10:
        return "Manipulated"
    return None

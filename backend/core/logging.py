"""
DeepShield Structured Logging
==============================
Configures logging for the backend. Call setup_logging() once at app startup.
"""
import logging
import sys

LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_inference(
    logger: logging.Logger,
    input_type: str,
    raw_prob: float,
    real_threshold: float,
    fake_threshold: float,
    classification: str,
    frame_count: int | None = None,
) -> None:
    """
    Structured log entry for every inference call.

    Args:
        input_type:      "image" or "video"
        raw_prob:        raw fake probability from the model (0–1)
        real_threshold:  threshold for "Authentic"
        fake_threshold:  threshold for "Manipulated"
        classification:  final label ("Authentic" / "Manipulated" / "Inconclusive")
        frame_count:     number of frames analysed (video only)
    """
    extra = f" | frames={frame_count}" if frame_count is not None else ""
    logger.info(
        f"[INFERENCE] type={input_type} | raw_prob={raw_prob:.6f} | "
        f"thresholds=(real≤{real_threshold}, fake≥{fake_threshold}) | "
        f"classification={classification}{extra}"
    )

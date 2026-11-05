# ============================================================
# FILE: core/logger.py
# TASK(S): Task 1 (Code Sanitization)
# CHANGES:
#   - Modified to replace core/logging.py context.
#   - Integrated requested custom formatting: [DeepShield][SERVICE_NAME]
#   - Replaced custom logger method with a configured stdlib logger instance factory.
#   - Removed redundant log_inference method in favor of standard formatting.
# ============================================================
"""
DeepShield Structured Logging
==============================
Configures logging for the backend. Call setup_logging() once at app startup.
"""
import logging
import sys

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class DeepShieldFormatter(logging.Formatter):
    """Custom formatter to enforce [DeepShield][SERVICE_NAME] style."""
    
    def format(self, record):
        service_name = record.name.split('.')[-1]
        if service_name.endswith('_service'):
            service_name = service_name.replace('_service', '').capitalize()
        elif service_name == 'main':
            service_name = 'startup'
        else:
            service_name = service_name
        
        # Inject custom prefix into the normal message
        record.msg = f"[DeepShield][{service_name}] {record.msg}"
        return super().format(record)

def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = DeepShieldFormatter(fmt="%(asctime)s | %(levelname)-7s | %(message)s", datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    
    root = logging.getLogger()
    root.setLevel(level)
    
    # Remove existing handlers to prevent duplicates
    if root.hasHandlers():
        root.handlers.clear()
        
    root.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger for the specified module name.
    """
    return logging.getLogger(name)

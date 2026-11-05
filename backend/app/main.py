"""
DeepShield FastAPI Application
================================
Entry point for the backend API server.

Run with:
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Or from the repo root:
    uvicorn backend.app.main:app --reload
"""
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Make the backend package root importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logging import setup_logging, get_logger
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from models.model_loader import load_model
from models.xception_loader import load_xception
from models.ai_classifier_loader import load_ai_classifier
from api.routes import router
from api.admin_routes import router as admin_router
from app.api.routes.auth import router as auth_router
from blockchain.node_manager import start_blockchain, stop_blockchain
from config import OUTPUTS_DIR

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load BOTH models before accepting requests; clean up on shutdown."""
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║       DeepShield Backend v2.1                ║")
    logger.info("║  UCF-Dominant Fusion + AI Detection          ║")
    logger.info("╚══════════════════════════════════════════════╝")

    # Load Xception (per-frame support signal + Grad-CAM++ for video)
    load_xception()
    logger.info("[Startup] Xception support model loaded.")

    # Load UCF (PRIMARY decision authority — images + video)
    load_model()
    logger.info("[Startup] UCF primary model loaded.")

    # Load AI classifier (OPTIONAL add-on — graceful fallback if absent)
    ai_model = load_ai_classifier()
    if ai_model is not None:
        logger.info("[Startup] AI classifier (trained) loaded.")
    else:
        logger.warning("[Startup] AI classifier weights absent — using heuristic fallback.")

    # Start local blockchain; failure is logged and never blocks analysis.
    import asyncio

    loop = asyncio.get_running_loop()
    blockchain_ok = await loop.run_in_executor(None, start_blockchain)
    if blockchain_ok:
        logger.info("[Startup] Local blockchain ready.")
    else:
        logger.warning("[Startup] Blockchain unavailable - analysis will still work.")

    logger.info("[Startup] Ready. Accepting requests.")
    yield
    stop_blockchain()
    logger.info("[Shutdown] DeepShield shutting down.")


app = FastAPI(
    title="DeepShield API",
    description=(
        "DeepShield v2.1 — UCF-dominant dual-model deepfake detection. "
        "UCF is the primary classifier; Xception is a frame-level support signal. "
        "4-band forensic system + AI-generated image detection + Grad-CAM++ explainability."
    ),
    version="2.1.0",
    lifespan=lifespan,
)


# CORS — allow all origins for development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve heatmap outputs as static files
import pathlib
pathlib.Path(OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# API routes
app.include_router(router)
app.include_router(admin_router)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "DeepShield",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "analyze": "POST /analyze",
    }

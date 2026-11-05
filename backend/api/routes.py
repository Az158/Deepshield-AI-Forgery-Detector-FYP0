"""
API Routes — /analyze and /health
===================================
"""
import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from blockchain import verify_on_chain
from blockchain.node_manager import get_contract_address
from core.auth import get_current_user, get_optional_current_user
from core.logger import get_logger
from reports import compute_pdf_report_hash, generate_pdf_report
from services.inference_service import analyze_image
from services.video_service import analyze_video
from models.model_loader import get_model
from config import OUTPUTS_DIR
import os
import uuid
from datetime import datetime, timezone
import services.supabase_service as supabase_service
from services.supabase_service import (
    compute_file_hash,
    check_duplicate,
    upload_heatmap,
    save_analysis,
    get_prior_analyses,
    upload_report,
    save_pdf_report,
    update_analysis_pdf_url,
    save_blockchain_anchor,
    save_dedup_reference,
    get_user_analyses,
)

logger = get_logger(__name__)

router = APIRouter()

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tiff"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "flv", "mpg", "mpeg"}


def _ext(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _cached_analysis_response(
    cached_record: dict,
    uploaded_filename: str | None,
    file_hash: str,
) -> dict:
    """Build the normal /analyze response from a previously saved analysis."""
    details = {
        "model": cached_record.get("model", "ucf"),
        "ucf_prob": cached_record.get("ucf_prob"),
        "ai_prob": cached_record.get("ai_prob"),
        "raw_logits": None,
        "frame_count": None,
        "aggregation_method": None,
    }

    return {
        "prediction": cached_record.get("prediction"),
        "confidence": cached_record.get("confidence"),
        "band": cached_record.get("band"),
        "type": cached_record.get("media_type"),
        "heatmap_url": cached_record.get("heatmap_url"),
        "thresholds": {
            "real": 0.35,
            "fake": 0.55,
        },
        "details": details,
        "processing_time_seconds": 0.0,
        "filename": uploaded_filename or cached_record.get("filename"),
        "analysis_id": cached_record.get("id"),
        "created_at": cached_record.get("created_at"),
        "file_hash": file_hash,
        "report_url": cached_record.get("pdf_url"),
        "blockchain_status": cached_record.get("blockchain_status", "pending"),
        "blockchain_tx_hash": cached_record.get("blockchain_tx_hash"),
        "polygon_url": cached_record.get("polygon_url"),
        "block_number": cached_record.get("block_number"),
        "is_duplicate": True,
        "prior_analyses": get_prior_analyses(file_hash),
    }


async def _run_post_analysis_tasks(
    analysis_id: str,
    analysis_result: dict,
) -> None:
    report_hash = None
    chain_result = {"error": "not_attempted"}

    try:
        logger.info(f"[PostAnalysis] Starting background tasks for analysis_id={analysis_id}")

        try:
            logger.info(f"[PostAnalysis] Computing PDF report hash for analysis_id={analysis_id}")
            report_hash = await run_in_threadpool(
                compute_pdf_report_hash, analysis_result, analysis_id
            )
            logger.info(f"[PostAnalysis] PDF report hash computed for analysis_id={analysis_id}")
        except Exception as exc:
            logger.exception(f"[PostAnalysis] PDF hash computation failed for analysis_id={analysis_id}: {exc}")
            return

        try:
            logger.info(f"[PostAnalysis] Anchoring report hash for analysis_id={analysis_id}")
            chain_result = await run_in_threadpool(verify_on_chain, report_hash, analysis_id)
            await run_in_threadpool(save_blockchain_anchor, analysis_id, report_hash, chain_result)
            logger.info(f"[PostAnalysis] Blockchain anchoring completed for analysis_id={analysis_id}")
        except Exception as exc:
            logger.exception(f"[PostAnalysis] Blockchain step failed for analysis_id={analysis_id}: {exc}")
            chain_result = {"error": "chain_unavailable", "detail": str(exc)}
            try:
                await run_in_threadpool(save_blockchain_anchor, analysis_id, report_hash, chain_result)
            except Exception as save_exc:
                logger.exception(f"[PostAnalysis] Failed to save blockchain failure for analysis_id={analysis_id}: {save_exc}")

        if "error" in chain_result:
            analysis_result.update({
                "blockchain_status": "failed",
                "blockchain_tx_hash": None,
                "block_number": None,
                "polygon_url": None,
            })
        else:
            analysis_result.update({
                "blockchain_status": chain_result.get("status", "confirmed"),
                "blockchain_tx_hash": chain_result.get("transaction_hash"),
                "block_number": chain_result.get("block_number"),
                "polygon_url": chain_result.get("verification_url"),
                "contract": chain_result.get("contract"),
                "chain": chain_result.get("chain"),
                "chain_id": chain_result.get("chain_id"),
            })

        try:
            logger.info(f"[PostAnalysis] Generating PDF report for analysis_id={analysis_id}")
            pdf_bytes, report_hash = await run_in_threadpool(
                generate_pdf_report, analysis_result, analysis_id, report_hash
            )
            logger.info(f"[PostAnalysis] PDF generated for analysis_id={analysis_id}")

            try:
                report_url = await run_in_threadpool(upload_report, pdf_bytes, analysis_id)
                logger.info(f"[PostAnalysis] PDF uploaded for analysis_id={analysis_id}")
            except Exception as exc:
                logger.exception(f"[PostAnalysis] PDF upload failed for analysis_id={analysis_id}: {exc}")
                report_url = None

            if report_url:
                try:
                    await run_in_threadpool(save_pdf_report, analysis_id, report_url, report_hash)
                    logger.info(f"[PostAnalysis] PDF report row saved for analysis_id={analysis_id}")
                except Exception as exc:
                    logger.exception(f"[PostAnalysis] PDF report row failed for analysis_id={analysis_id}: {exc}")

                try:
                    await run_in_threadpool(update_analysis_pdf_url, analysis_id, report_url)
                    logger.info(f"[PostAnalysis] Analysis PDF URL updated for analysis_id={analysis_id}")
                except Exception as exc:
                    logger.exception(f"[PostAnalysis] Analysis PDF URL update failed for analysis_id={analysis_id}: {exc}")
        except Exception as exc:
            logger.exception(f"[PostAnalysis] PDF generation failed for analysis_id={analysis_id}: {exc}")
    except Exception as exc:
        logger.exception(f"[PostAnalysis] Unexpected background failure for analysis_id={analysis_id}: {exc}")


# ── POST /analyze ────────────────────────────────────────────────────────────

@router.post("/analyze", summary="Analyze an image or video for deepfake manipulation")
async def analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict | None = Depends(get_optional_current_user),
):
    """
    Analyze an uploaded image or video file for deepfake manipulation.

    - **Image**: Returns prediction, confidence, Grad-CAM heatmap URL.
    - **Video**: Extracts frames (uniform sampling), infers per-frame, aggregates via mean.

    Returns:
    ```json
    {
      "prediction": "Manipulated | Authentic | Inconclusive",
      "confidence": 0.91,
      "type": "image | video",
      "heatmap_url": "/outputs/heatmap_xxx.png",
      "thresholds": { "real": 0.3, "fake": 0.7 },
      "details": {
        "frame_count": null,
        "aggregation_method": null
      }
    }
    ```
    """
    ext = _ext(file.filename)
    if ext in IMAGE_EXTENSIONS:
        media_type = "image"
    elif ext in VIDEO_EXTENSIONS:
        media_type = "video"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. "
                   f"Accepted images: {IMAGE_EXTENSIONS}. "
                   f"Accepted videos: {VIDEO_EXTENSIONS}."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file received.")

    user_id = current_user["user_id"] if current_user else None

    # Step 1: Read file bytes and compute hash
    file_hash = compute_file_hash(file_bytes)

    # Step 2: Check for duplicate before running expensive model work.
    cached_record = check_duplicate(file_hash)
    if cached_record:
        original_analysis_id = cached_record.get("id")
        logger.info(
            f"[API] /analyze cache hit - original_id={original_analysis_id}, "
            f"file={file.filename!r}, type={media_type}, size={len(file_bytes)} bytes"
        )
        cached_analysis = supabase_service.get_analysis_by_id(original_analysis_id)
        if cached_analysis:
            cached_analysis.setdefault(
                "media_type",
                cached_record.get("media_type", media_type),
            )
            cached_analysis.setdefault("filename", cached_record.get("filename"))
            cached_analysis.setdefault("created_at", cached_record.get("created_at"))
            cached_response = _cached_analysis_response(
                cached_analysis,
                file.filename,
                file_hash,
            )

            if user_id:
                duplicate_analysis_id = str(uuid.uuid4())
                cached_response["analysis_id"] = duplicate_analysis_id
                cached_response["id"] = duplicate_analysis_id
                cached_response["original_analysis_id"] = original_analysis_id
                cached_response["created_at"] = datetime.now(timezone.utc).isoformat()
                cached_response["filename"] = file.filename or cached_response.get("filename")
                save_analysis(
                    duplicate_analysis_id,
                    file_hash,
                    cached_response["filename"],
                    cached_response,
                    user_id=user_id,
                )
                if original_analysis_id:
                    save_dedup_reference(file_hash, original_analysis_id, duplicate_analysis_id)
                cached_response["prior_analyses"] = get_prior_analyses(file_hash)

            return JSONResponse(content=cached_response)
        logger.warning(
            f"[API] Duplicate hash found but analysis {original_analysis_id} "
            "could not be loaded. Falling back to fresh analysis."
        )

    # Step 3: Generate a new analysis ID for new content.
    new_analysis_id = str(uuid.uuid4())

    t0 = time.perf_counter()
    logger.info(
        f"[API] /analyze - id={new_analysis_id}, file={file.filename!r}, "
        f"type={media_type}, size={len(file_bytes)} bytes, dup=False"
    )

    try:
        if media_type == "image":
            result = analyze_image(file_bytes)
        else:
            result = analyze_video(file_bytes)
    except ValueError as exc:
        logger.warning(f"[API] Analysis error: {exc}")
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception(f"[API] Unexpected error during analysis")
        raise HTTPException(status_code=500, detail="Internal server error during analysis.")

    elapsed = round(time.perf_counter() - t0, 3)
    result["processing_time_seconds"] = elapsed
    result["filename"] = file.filename
    result["analysis_id"] = new_analysis_id
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    result["file_hash"] = file_hash
    result["report_url"] = None
    result["blockchain_status"] = "pending"

    # Step 5: Upload heatmap to Supabase Storage
    local_heatmap_url = result.get("heatmap_url")
    if local_heatmap_url and local_heatmap_url.startswith("/outputs/"):
        filename = os.path.basename(local_heatmap_url)
        local_path = os.path.join(OUTPUTS_DIR, filename)
        if os.path.exists(local_path):
            supa_url = upload_heatmap(local_path, new_analysis_id)
            if supa_url is not None:
                result["heatmap_url"] = supa_url
            else:
                result["heatmap_url"] = None

    # Step 6: Save to database
    save_analysis(new_analysis_id, file_hash, file.filename, result, user_id=user_id)

    # Step 7: Fetch prior analyses
    prior_analyses = get_prior_analyses(file_hash)
    
    # Ensure current analysis is in the list even if save_analysis failed silently
    if not any(row.get("id") == new_analysis_id for row in prior_analyses):
        current_summary = {
            "id": new_analysis_id,
            "prediction": result.get("prediction"),
            "confidence": result.get("confidence"),
            "band": result.get("band", result.get("details", {}).get("band")),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "heatmap_url": result.get("heatmap_url")
        }
        prior_analyses.append(current_summary)

    # Step 8: Extend and return response
    result["is_duplicate"] = False
    result["prior_analyses"] = prior_analyses

    background_tasks.add_task(
        _run_post_analysis_tasks,
        new_analysis_id,
        result,
    )

    return JSONResponse(content=result, background=background_tasks)


@router.get("/analyses/history", summary="Get user's analysis history")
async def get_user_history(
    current_user: dict = Depends(get_current_user)
):
    """Returns all analyses for the authenticated user, newest first."""
    results = supabase_service.get_user_analyses(current_user["user_id"])
    return {"analyses": results}


@router.get("/verify/{analysis_id}")
async def verify_analysis_public(analysis_id: str):
    """
    Public verification endpoint - NO authentication required.
    Called by QR codes embedded in PDF forensic reports.
    Returns blockchain anchoring status for any analysis by UUID.
    """
    try:
        analysis_result = supabase_service.get_analysis_by_id(analysis_id)
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis not found.")

        try:
            bc = supabase_service.supabase.table("blockchain_anchors") \
                .select("tx_hash, block_number, polygon_url, status, report_hash, anchored_at") \
                .eq("analysis_id", analysis_id) \
                .single() \
                .execute()
            blockchain_data = bc.data if bc.data else {}
        except Exception:
            try:
                bc = supabase_service.supabase.table("blockchain_anchors") \
                    .select("tx_hash, block_number, polygon_url, status, report_hash") \
                    .eq("analysis_id", analysis_id) \
                    .single() \
                    .execute()
                blockchain_data = bc.data if bc.data else {}
            except Exception:
                blockchain_data = {}

        return {
            "analysis_id": analysis_id,
            "filename": analysis_result.get("filename"),
            "prediction": analysis_result.get("prediction"),
            "confidence": analysis_result.get("confidence"),
            "band": analysis_result.get("band"),
            "media_type": analysis_result.get("media_type"),
            "created_at": analysis_result.get("created_at"),
            "blockchain_status": blockchain_data.get("status", "pending"),
            "report_hash": blockchain_data.get("report_hash"),
            "tx_hash": blockchain_data.get("tx_hash"),
            "block_number": blockchain_data.get("block_number"),
            "anchored_at": blockchain_data.get("anchored_at"),
            "chain": "DeepShield Private Chain (Hardhat / EVM-compatible)",
            "chain_id": 31337,
            "contract_address": get_contract_address()
            or "0x5FbDB2315678afecb367f032d93F642f64180aa3",
            "verified": blockchain_data.get("status") == "confirmed",
            "verification_note": (
                "This report hash was anchored on a private EVM-compatible blockchain. "
                "The tx_hash and block_number provide cryptographic proof that this "
                "specific forensic report existed at the time of anchoring and has "
                "not been modified since."
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Verify] Error for {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Verification lookup failed.")


@router.get("/analyses/{analysis_id}")
async def get_analysis_by_id(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns a single analysis record by UUID."""
    result = supabase_service.get_analysis_by_id(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result


# ── GET /health ──────────────────────────────────────────────────────────────

@router.get("/health", summary="Health check")
def health():
    """Returns API status and model readiness."""
    try:
        model = get_model()
        model_loaded = model is not None
    except RuntimeError:
        model_loaded = False

    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "service": "DeepShield",
        "version": "1.0.0",
    }

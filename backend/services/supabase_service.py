import os
import hashlib
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Only load_dotenv if it hasn't been done yet, though main.py will also do it.
load_dotenv()

def get_supabase_client() -> Optional[Client]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = get_supabase_client()


def log_admin_event(
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Write a system-level audit event for the admin dashboard."""
    if not supabase:
        return

    try:
        supabase.table("admin_audit_logs").insert({
            "admin_user_id": None,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
        }).execute()
    except Exception as exc:
        logger.warning(f"[Supabase] Admin audit log skipped for action={action}: {exc}")

def compute_file_hash(file_bytes: bytes) -> str:
    """Compute and return the SHA-256 hex digest of the raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()

def check_duplicate(file_hash: str) -> Optional[Dict[str, Any]]:
    """
    Query the analyses table for the most recent row where file_hash matches.
    If found, return the full row as a dict. If not found, return None.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. check_duplicate returning None.")
        return None
    
    try:
        # Order by created_at descending to get the most recent one
        response = supabase.table("analyses").select("*").eq("file_hash", file_hash).order("created_at", desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as exc:
        logger.error(f"[Supabase] Error checking duplicate for hash {file_hash}: {exc}")
        return None

def upload_heatmap(local_path: str, analysis_id: str) -> Optional[str]:
    """
    Upload the heatmap PNG file from local_path to the heatmaps Supabase Storage bucket.
    Use the path {analysis_id}/heatmap.png as the storage key. Return the public URL string.
    After a successful upload, delete the local file.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. upload_heatmap returning None.")
        return None

    storage_path = f"{analysis_id}/heatmap.png"
    
    try:
        with open(local_path, "rb") as f:
            # We use file_options to set content type
            supabase.storage.from_("heatmaps").upload(
                file=f,
                path=storage_path,
                file_options={"content-type": "image/png"}
            )
            
        public_url = supabase.storage.from_("heatmaps").get_public_url(storage_path)
        
        # Delete local file after successful upload
        try:
            os.remove(local_path)
        except OSError as e:
            logger.warning(f"[Supabase] Failed to delete local heatmap {local_path}: {e}")
            
        return public_url
    except Exception as exc:
        logger.error(f"[Supabase] Error uploading heatmap {local_path}: {exc}")
        return None

def save_analysis(
    analysis_id: str,
    file_hash: str,
    filename: str,
    response_data: Dict[str, Any],
    user_id: Optional[str] = None,
) -> None:
    """
    Insert one row into the analyses table.
    Map fields from response_data plus the file_hash and filename.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. update skipped.")
        return
        
    try:
        record = {
            "id": analysis_id,
            "file_hash": file_hash,
            "filename": filename,
            "user_id": user_id,
            "media_type": response_data.get("type"), # Either 'image' or 'video', in response_data it's returned as type
            "prediction": response_data.get("prediction"),
            "confidence": response_data.get("confidence"),
            # 'band' is not in the basic response but let's check if it exists or if we need to get it from details
            "band": response_data.get("band", response_data.get("details", {}).get("band")),
            # ucf_prob and ai_prob might only be in details
            "ucf_prob": response_data.get("details", {}).get("ucf_prob", response_data.get("ucf_prob")),
            "ai_prob": response_data.get("details", {}).get("ai_prob", response_data.get("ai_prob")),
            "heatmap_url": response_data.get("heatmap_url"),
            "pdf_url": response_data.get("pdf_url") or response_data.get("report_url"),
            "blockchain_status": response_data.get("blockchain_status"),
            "blockchain_tx_hash": response_data.get("blockchain_tx_hash"),
            "block_number": response_data.get("block_number"),
            "polygon_url": response_data.get("polygon_url"),
        }
        
        # Filter out None values that aren't expected by supabase tables,
        # but supabase expects explicitly null for some things.
        # Actually it's better to just pass the dictionary.
        record = {k: v for k, v in record.items() if v is not None}
        
        supabase.table("analyses").insert(record).execute()
        log_admin_event(
            "analysis.created",
            "analysis",
            analysis_id,
            {
                "filename": filename,
                "prediction": response_data.get("prediction"),
                "confidence": response_data.get("confidence"),
                "media_type": response_data.get("type"),
            },
        )
    except Exception as exc:
        logger.error(f"[Supabase] Error saving analysis {analysis_id}: {exc}")

def save_dedup_reference(file_hash: str, original_analysis_id: str, duplicate_analysis_id: str) -> None:
    """
    Insert one row into dedup_references.
    Called only when a duplicate file hash is detected.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. save_dedup skipped.")
        return
        
    try:
        record = {
            "file_hash": file_hash,
            "original_analysis_id": original_analysis_id,
            "duplicate_analysis_id": duplicate_analysis_id
        }
        supabase.table("dedup_references").insert(record).execute()
        log_admin_event(
            "analysis.duplicate_detected",
            "analysis",
            duplicate_analysis_id,
            {
                "file_hash": file_hash,
                "original_analysis_id": original_analysis_id,
            },
        )
    except Exception as exc:
        # "log the error and continue silently"
        logger.error(f"[Supabase] Error saving dedup reference original={original_analysis_id} dup={duplicate_analysis_id}: {exc}")

def get_prior_analyses(file_hash: str) -> List[Dict[str, Any]]:
    """
    Query analyses for all rows with the given file_hash, ordered by created_at ascending.
    Return as a list of dicts containing only: id, prediction, confidence, band, created_at, heatmap_url.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. get_prior_analyses returning [].")
        return []
        
    try:
        columns = "id, prediction, confidence, band, created_at, heatmap_url"
        response = supabase.table("analyses").select(columns).eq("file_hash", file_hash).order("created_at").execute()
        return response.data if response.data else []
    except Exception as exc:
        logger.error(f"[Supabase] Error getting prior analyses for hash {file_hash}: {exc}")
        return []


def upload_report(pdf_bytes: bytes, analysis_id: str) -> str:
    """Upload a generated PDF report to Supabase Storage."""
    if not supabase:
        raise RuntimeError("Supabase client not initialized.")

    storage_path = f"{analysis_id}/report.pdf"

    try:
        supabase.storage.from_("reports").upload(
            file=pdf_bytes,
            path=storage_path,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )
        return supabase.storage.from_("reports").get_public_url(storage_path)
    except Exception as exc:
        logger.error(f"[Supabase] Error uploading PDF report for analysis {analysis_id}: {exc}")
        raise


def save_pdf_report(analysis_id: str, file_url: str, report_hash: str) -> None:
    """Insert generated PDF metadata into the pdf_reports table."""
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. save_pdf_report skipped.")
        return

    try:
        record = {
            "analysis_id": analysis_id,
            "file_url": file_url,
            "report_hash": report_hash,
            "generated_at": datetime.utcnow().isoformat(),
        }
        supabase.table("pdf_reports").insert(record).execute()
        log_admin_event(
            "report.generated",
            "analysis",
            analysis_id,
            {"report_hash": report_hash, "file_url": file_url},
        )
    except Exception as exc:
        logger.error(f"[Supabase] Error saving PDF report for analysis {analysis_id}: {exc}")


def update_analysis_pdf_url(analysis_id: str, pdf_url: str) -> None:
    """Update the analysis row with the generated PDF URL."""
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. update_analysis_pdf_url skipped.")
        return

    try:
        supabase.table("analyses").update({"pdf_url": pdf_url}).eq("id", analysis_id).execute()
    except Exception as exc:
        logger.error(f"[Supabase] Error updating PDF URL for analysis {analysis_id}: {exc}")


def save_blockchain_anchor(analysis_id: str, report_hash: str, result: dict) -> None:
    """
    Save blockchain anchoring result to blockchain_anchors table
    AND update the analyses row with status, tx_hash, block_number, polygon_url.
    """
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. save_blockchain_anchor skipped.")
        return

    try:
        if "error" in result:
            supabase.table("blockchain_anchors").insert({
                "analysis_id": analysis_id,
                "report_hash": report_hash,
                "tx_hash": None,
                "block_number": None,
                "polygon_url": None,
                "status": "failed",
            }).execute()

            supabase.table("analyses").update({
                "blockchain_status": "failed",
            }).eq("id", analysis_id).execute()
            log_admin_event(
                "blockchain.anchor_failed",
                "analysis",
                analysis_id,
                {
                    "report_hash": report_hash,
                    "error": result.get("error"),
                    "detail": result.get("detail"),
                },
            )
        else:
            tx_hash = result.get("transaction_hash")
            block_number = result.get("block_number")
            polygon_url = result.get("verification_url")

            supabase.table("blockchain_anchors").insert({
                "analysis_id": analysis_id,
                "report_hash": report_hash,
                "tx_hash": tx_hash,
                "block_number": block_number,
                "polygon_url": polygon_url,
                "status": "confirmed",
            }).execute()

            supabase.table("analyses").update({
                "blockchain_status": "confirmed",
                "blockchain_tx_hash": tx_hash,
                "block_number": block_number,
                "polygon_url": polygon_url,
            }).eq("id", analysis_id).execute()
            log_admin_event(
                "blockchain.anchor_confirmed",
                "analysis",
                analysis_id,
                {
                    "report_hash": report_hash,
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                },
            )

    except Exception as e:
        logger.error(f"[Supabase] Error saving blockchain anchor for {analysis_id}: {e}")


def get_analysis_by_id(analysis_id: str) -> dict | None:
    """Fetch a single analysis record by UUID, including blockchain status."""
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. get_analysis_by_id returning None.")
        return None

    try:
        result = supabase.table("analyses")\
            .select("id, filename, prediction, confidence, band, heatmap_url, pdf_url, created_at, media_type, ucf_prob, ai_prob")\
            .eq("id", analysis_id)\
            .execute()

        if not result.data:
            return None

        analysis = result.data[0]

        try:
            bc_result = supabase.table("blockchain_anchors")\
                .select("tx_hash, block_number, polygon_url, status")\
                .eq("analysis_id", analysis_id)\
                .execute()

            bc_data = bc_result.data[0] if bc_result.data else None
            if bc_data:
                analysis["blockchain_status"] = bc_data.get("status", "pending")
                analysis["blockchain_tx_hash"] = bc_data.get("tx_hash")
                analysis["polygon_url"] = bc_data.get("polygon_url")
                analysis["block_number"] = bc_data.get("block_number")
            else:
                analysis["blockchain_status"] = "pending"
                analysis["blockchain_tx_hash"] = None
                analysis["polygon_url"] = None
                analysis["block_number"] = None
        except Exception:
            analysis["blockchain_status"] = "pending"
            analysis["blockchain_tx_hash"] = None
            analysis["polygon_url"] = None
            analysis["block_number"] = None

        return analysis
    except Exception as exc:
        logger.error(f"[Supabase] Error fetching analysis {analysis_id}: {exc}")
        return None


def get_user_analyses(user_id: str) -> list[dict]:
    """Fetch all analyses for a user, ordered newest first."""
    if not supabase:
        logger.warning("[Supabase] Supabase client not initialized. get_user_analyses returning [].")
        return []
    
    try:
        result = supabase.table("analyses")\
            .select("id, filename, prediction, confidence, band, "
                    "heatmap_url, pdf_url, created_at, media_type, "
                    "ucf_prob, ai_prob, file_hash, blockchain_status, "
                    "blockchain_tx_hash, polygon_url, block_number")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return result.data if result.data else []
    except Exception as exc:
        logger.error(f"[Supabase] Error fetching user analyses for {user_id}: {exc}")
        return []

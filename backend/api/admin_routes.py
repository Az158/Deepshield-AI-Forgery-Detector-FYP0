"""
Admin API routes for the DeepShield investigator dashboard.

These endpoints use Supabase auth for identity and the admin_profiles table
for role-based access control.
"""

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.auth import get_current_user
from core.logger import get_logger
from services import supabase_service

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_ROLES = {"admin", "investigator", "viewer"}
WRITE_ROLES = {"admin", "investigator"}


class ReviewStatusUpdate(BaseModel):
    reviewed_status: str


class ReviewNoteCreate(BaseModel):
    note: str


class UserStatusUpdate(BaseModel):
    role: str | None = None
    status: str | None = None


class SettingUpdate(BaseModel):
    value: dict[str, Any]


def _require_supabase():
    if not supabase_service.supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return supabase_service.supabase


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_fake(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "").lower()
        for key in ("prediction", "band")
    )
    return any(word in text for word in ("fake", "manipulated", "ai-generated"))


def _role_rank(role: str) -> int:
    return {"viewer": 1, "investigator": 2, "admin": 3}.get(role, 0)


async def require_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    supabase = _require_supabase()
    user_id = current_user["user_id"]

    try:
        result = supabase.table("admin_profiles") \
            .select("id, display_name, role, status, last_active_at") \
            .eq("id", user_id) \
            .single() \
            .execute()
    except Exception as exc:
        logger.warning(f"[Admin] Role lookup failed for user_id={user_id}: {exc}")
        raise HTTPException(status_code=403, detail="Admin access required.")

    profile = result.data if result and result.data else None
    if not profile:
        raise HTTPException(status_code=403, detail="Admin access required.")

    role = profile.get("role")
    status = profile.get("status")
    if role not in ADMIN_ROLES or status != "active":
        raise HTTPException(status_code=403, detail="Admin access required.")

    try:
        supabase.table("admin_profiles").update({
            "last_active_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", user_id).execute()
    except Exception:
        pass

    return {
        **current_user,
        "role": role,
        "display_name": profile.get("display_name"),
    }


def _require_write(admin: dict) -> None:
    if admin.get("role") not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Write access required.")


def _require_owner_admin(admin: dict) -> None:
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required.")


def _log_admin_action(
    admin_user_id: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    supabase = _require_supabase()
    try:
        supabase.table("admin_audit_logs").insert({
            "admin_user_id": admin_user_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
        }).execute()
    except Exception as exc:
        logger.warning(f"[Admin] Failed to write audit log: {exc}")


@router.get("/me")
async def admin_me(admin: dict = Depends(require_admin_user)):
    return admin


@router.get("/metrics")
async def admin_metrics(admin: dict = Depends(require_admin_user)):
    supabase = _require_supabase()
    analyses = supabase.table("analyses") \
        .select("id, created_at, media_type, prediction, confidence, band, blockchain_status") \
        .order("created_at", desc=True) \
        .limit(1000) \
        .execute().data or []

    total = len(analyses)
    fake_count = sum(1 for row in analyses if _is_fake(row))
    confirmed = sum(1 for row in analyses if row.get("blockchain_status") == "confirmed")
    confidences = [
        value for value in (_coerce_float(row.get("confidence")) for row in analyses)
        if value is not None
    ]

    by_day: dict[str, int] = {}
    by_media: dict[str, int] = {}
    by_prediction: dict[str, int] = {}
    for row in analyses:
        created = str(row.get("created_at") or "")[:10] or "unknown"
        by_day[created] = by_day.get(created, 0) + 1
        media = row.get("media_type") or "unknown"
        by_media[media] = by_media.get(media, 0) + 1
        prediction = row.get("prediction") or "Unknown"
        by_prediction[prediction] = by_prediction.get(prediction, 0) + 1

    return {
        "total_analyses": total,
        "fake_rate": round((fake_count / total) * 100, 2) if total else 0,
        "average_confidence": round(mean(confidences) * 100, 2) if confidences else 0,
        "blockchain_confirmed_rate": round((confirmed / total) * 100, 2) if total else 0,
        "trend": [
            {"date": key, "count": by_day[key]}
            for key in sorted(by_day.keys())[-14:]
        ],
        "media_breakdown": by_media,
        "prediction_breakdown": by_prediction,
        "alerts": [
            {
                "type": "blockchain",
                "message": f"{total - confirmed} analyses are not confirmed on-chain.",
                "severity": "warning" if total - confirmed else "ok",
            }
        ],
    }


@router.get("/analyses")
async def admin_analyses(
    prediction: str | None = None,
    media_type: str | None = None,
    blockchain_status: str | None = None,
    reviewed_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(require_admin_user),
):
    supabase = _require_supabase()
    query = supabase.table("analyses").select(
        "id, user_id, filename, media_type, prediction, confidence, band, "
        "ucf_prob, ai_prob, heatmap_url, pdf_url, created_at, block_number, "
        "blockchain_tx_hash, polygon_url, blockchain_status, reviewed_status"
    )
    if prediction:
        query = query.eq("prediction", prediction)
    if media_type:
        query = query.eq("media_type", media_type)
    if blockchain_status:
        query = query.eq("blockchain_status", blockchain_status)
    if reviewed_status:
        query = query.eq("reviewed_status", reviewed_status)

    rows = query.order("created_at", desc=True).limit(limit).execute().data or []
    return {"analyses": rows}


@router.get("/analyses/{analysis_id}")
async def admin_analysis_detail(
    analysis_id: str,
    admin: dict = Depends(require_admin_user),
):
    supabase = _require_supabase()
    result = supabase.table("analyses").select("*").eq("id", analysis_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    anchors = supabase.table("blockchain_anchors").select("*").eq("analysis_id", analysis_id).execute().data or []
    reports = supabase.table("pdf_reports").select("*").eq("analysis_id", analysis_id).execute().data or []
    notes = supabase.table("analysis_review_notes").select("*").eq("analysis_id", analysis_id).order("created_at", desc=True).execute().data or []
    dedup = supabase.table("dedup_references").select("*").or_(
        f"original_analysis_id.eq.{analysis_id},duplicate_analysis_id.eq.{analysis_id}"
    ).execute().data or []

    return {
        "analysis": result.data,
        "blockchain_anchors": anchors,
        "pdf_reports": reports,
        "review_notes": notes,
        "dedup_references": dedup,
    }


@router.patch("/analyses/{analysis_id}/review-status")
async def update_review_status(
    analysis_id: str,
    payload: ReviewStatusUpdate,
    admin: dict = Depends(require_admin_user),
):
    _require_write(admin)
    if payload.reviewed_status not in {"unreviewed", "reviewed", "flagged", "dismissed"}:
        raise HTTPException(status_code=400, detail="Invalid review status.")

    supabase = _require_supabase()
    supabase.table("analyses").update({
        "reviewed_status": payload.reviewed_status,
        "reviewed_by": admin["user_id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", analysis_id).execute()
    _log_admin_action(
        admin["user_id"],
        "analysis.review_status_updated",
        "analysis",
        analysis_id,
        {"reviewed_status": payload.reviewed_status},
    )
    return {"status": "ok"}


@router.post("/analyses/{analysis_id}/notes")
async def add_review_note(
    analysis_id: str,
    payload: ReviewNoteCreate,
    admin: dict = Depends(require_admin_user),
):
    _require_write(admin)
    note = payload.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Note cannot be empty.")

    supabase = _require_supabase()
    row = {
        "analysis_id": analysis_id,
        "admin_user_id": admin["user_id"],
        "note": note,
    }
    result = supabase.table("analysis_review_notes").insert(row).execute()
    _log_admin_action(admin["user_id"], "analysis.note_added", "analysis", analysis_id)
    return {"note": (result.data or [row])[0]}


@router.get("/users")
async def admin_users(admin: dict = Depends(require_admin_user)):
    supabase = _require_supabase()
    profiles = supabase.table("admin_profiles") \
        .select("id, display_name, role, status, created_at, last_active_at") \
        .order("created_at", desc=True) \
        .execute().data or []
    return {"users": profiles}


@router.patch("/users/{user_id}")
async def update_admin_user(
    user_id: str,
    payload: UserStatusUpdate,
    admin: dict = Depends(require_admin_user),
):
    _require_owner_admin(admin)
    updates: dict[str, Any] = {}
    if payload.role is not None:
        if payload.role not in ADMIN_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role.")
        if _role_rank(payload.role) > _role_rank(admin["role"]):
            raise HTTPException(status_code=403, detail="Cannot grant that role.")
        updates["role"] = payload.role
    if payload.status is not None:
        if payload.status not in {"active", "suspended"}:
            raise HTTPException(status_code=400, detail="Invalid status.")
        updates["status"] = payload.status

    if not updates:
        return {"status": "no_changes"}

    supabase = _require_supabase()
    supabase.table("admin_profiles").update(updates).eq("id", user_id).execute()
    _log_admin_action(admin["user_id"], "admin_user.updated", "admin_profile", user_id, updates)
    return {"status": "ok"}


@router.get("/settings")
async def admin_settings(admin: dict = Depends(require_admin_user)):
    supabase = _require_supabase()
    rows = supabase.table("system_settings").select("*").execute().data or []
    return {"settings": rows}


@router.patch("/settings/{key}")
async def update_setting(
    key: str,
    payload: SettingUpdate,
    admin: dict = Depends(require_admin_user),
):
    _require_owner_admin(admin)
    supabase = _require_supabase()
    row = {
        "key": key,
        "value": payload.value,
        "updated_by": admin["user_id"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("system_settings").upsert(row).execute()
    _log_admin_action(admin["user_id"], "setting.updated", "system_setting", None, {"key": key})
    return {"setting": row}


@router.get("/audit-logs")
async def admin_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    admin: dict = Depends(require_admin_user),
):
    supabase = _require_supabase()
    rows = supabase.table("admin_audit_logs") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute().data or []
    return {"logs": rows}


@router.get("/blockchain/status")
async def blockchain_status(admin: dict = Depends(require_admin_user)):
    supabase = _require_supabase()
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = supabase.table("blockchain_anchors") \
        .select("status, block_number, anchored_at") \
        .gte("anchored_at", since) \
        .execute().data or []
    confirmed = [row for row in rows if row.get("status") == "confirmed"]
    failed = [row for row in rows if row.get("status") == "failed"]
    latest_block = max(
        (row.get("block_number") or 0 for row in confirmed),
        default=None,
    )
    return {
        "chain": "DeepShield Private Chain",
        "chain_id": 31337,
        "status": "healthy" if rows and not failed else "attention",
        "confirmed_last_7_days": len(confirmed),
        "failed_last_7_days": len(failed),
        "latest_block": latest_block,
    }

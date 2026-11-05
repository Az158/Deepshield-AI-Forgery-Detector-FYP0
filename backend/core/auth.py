import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

from core.logger import get_logger

load_dotenv()

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


def _auth_client():
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        logger.error("[Auth] Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
        raise HTTPException(status_code=401, detail="Authentication required.")
    return create_client(url, anon_key)


def _get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    try:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authentication required.")

        scheme = getattr(credentials, "scheme", "") or ""
        token = getattr(credentials, "credentials", "") or ""
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Authentication required.")

        response = _auth_client().auth.get_user(token.strip())
        user = _get_attr(response, "user")
        user_id = _get_attr(user, "id")
        email = _get_attr(user, "email")
        if not user or not user_id or not email:
            raise ValueError("Supabase did not return a valid user.")
        return {"user_id": str(user_id), "email": str(email)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"[Auth] Token verification failed: {exc}")
        raise HTTPException(status_code=401, detail="Authentication required.")


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Return the authenticated Supabase user when a valid bearer token is present.
    Anonymous requests are allowed and return None.
    """
    if credentials is None:
        return None

    try:
        scheme = getattr(credentials, "scheme", "") or ""
        token = getattr(credentials, "credentials", "") or ""
        if scheme.lower() != "bearer" or not token.strip():
            return None

        response = _auth_client().auth.get_user(token.strip())
        user = _get_attr(response, "user")
        user_id = _get_attr(user, "id")
        email = _get_attr(user, "email")
        if not user or not user_id:
            return None
        return {"user_id": str(user_id), "email": str(email or "")}
    except Exception as exc:
        logger.warning(f"[Auth] Optional token verification failed: {exc}")
        return None

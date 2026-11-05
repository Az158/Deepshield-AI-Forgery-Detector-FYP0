import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import create_client

from app.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    SignupRequest,
    SignupResponse,
)
from core.auth import get_current_user
from core.logger import get_logger

load_dotenv()

logger = get_logger(__name__)
router = APIRouter()


def _auth_client():
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        logger.error("[Auth] Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
        raise HTTPException(status_code=400, detail="Authentication service is not configured.")
    return create_client(url, anon_key)


def _get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication required.")
    return token.strip()


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: SignupRequest) -> SignupResponse:
    try:
        response = _auth_client().auth.sign_up(
            {"email": str(payload.email), "password": payload.password}
        )
        user = _get_attr(response, "user")
        user_id = _get_attr(user, "id")
        if not user or not user_id:
            raise ValueError("Supabase did not return a user for signup.")
        return SignupResponse(
            message="Account created. Please verify your email before logging in.",
            user_id=str(user_id),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"[Auth] Signup failed for email={payload.email}: {exc}")
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists.",
        )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    try:
        response = _auth_client().auth.sign_in_with_password(
            {"email": str(payload.email), "password": payload.password}
        )
        session = _get_attr(response, "session")
        user = _get_attr(response, "user")
        access_token = _get_attr(session, "access_token")
        expires_in = _get_attr(session, "expires_in")
        user_id = _get_attr(user, "id")
        email = _get_attr(user, "email")
        if not access_token or not user_id or not email:
            raise ValueError("Supabase did not return a complete session.")
        return LoginResponse(
            access_token=str(access_token),
            expires_in=int(expires_in or 3600),
            user_id=str(user_id),
            email=str(email),
        )
    except Exception as exc:
        logger.warning(f"[Auth] Login failed for email={payload.email}: {exc}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")


@router.post("/logout", response_model=MessageResponse)
def logout(
    authorization: str | None = Header(default=None),
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    token = _extract_bearer_token(authorization)
    try:
        client = _auth_client()
        try:
            client.auth.sign_out(token)
        except Exception:
            _sign_out_via_rest(token)
    except Exception as exc:
        logger.warning(f"[Auth] Logout failed for user_id={current_user.get('user_id')}: {exc}")
    return MessageResponse(message="Logged out successfully.")


def _sign_out_via_rest(token: str) -> None:
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise ValueError("Supabase auth configuration is missing.")

    request = Request(
        f"{url.rstrip('/')}/auth/v1/logout",
        method="POST",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Length": "0",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError("Supabase sign-out request failed.") from exc

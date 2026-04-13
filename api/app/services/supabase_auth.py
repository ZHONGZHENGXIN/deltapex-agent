import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_supabase_user_id,
    get_user_by_username,
    is_first_user,
)
from app.models.user import User, UserType

logger = get_logger(__name__)

_JWKS_CACHE: dict[str, Any] = {"keys": None, "expires_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _require_supabase_settings() -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase auth is not configured on the server",
        )


def _fetch_jwks(force_refresh: bool = False) -> list[dict[str, Any]]:
    _require_supabase_settings()

    now = time.time()
    cached_keys = _JWKS_CACHE.get("keys")
    if not force_refresh and cached_keys and _JWKS_CACHE["expires_at"] > now:
        return cached_keys

    assert settings.SUPABASE_JWKS_URL is not None
    response = httpx.get(settings.SUPABASE_JWKS_URL, timeout=10.0)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
    return keys


def verify_supabase_access_token(token: str) -> dict[str, Any]:
    _require_supabase_settings()

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    kid = header.get("kid")
    algorithm = header.get("alg", "RS256")
    keys = _fetch_jwks()
    key = next((item for item in keys if item.get("kid") == kid), None)

    if key is None:
        keys = _fetch_jwks(force_refresh=True)
        key = next((item for item in keys if item.get("kid") == kid), None)

    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=settings.SUPABASE_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def _sanitize_username(value: Optional[str]) -> str:
    if not value:
        return "user"

    sanitized = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fa5]", "_", value).strip("_")
    return sanitized or "user"


def _build_unique_username(base_username: str, session: Session) -> str:
    base = _sanitize_username(base_username)[:20]
    if len(base) < 2:
        base = f"user_{base}".strip("_")[:20]

    candidate = base
    suffix = 1
    while True:
        existing = get_user_by_username(candidate, session)
        if not existing:
            return candidate
        suffix_str = str(suffix)
        candidate = f"{base[: max(1, 20 - len(suffix_str) - 1)]}_{suffix_str}"
        suffix += 1


def _extract_username(claims: dict[str, Any], email: str, session: Session) -> str:
    metadata = claims.get("user_metadata") or {}
    preferred = metadata.get("username") or metadata.get("name")
    if not preferred:
        preferred = email.split("@", 1)[0]
    return _build_unique_username(preferred, session)


def sync_local_user_from_supabase(session: Session, claims: dict[str, Any]) -> User:
    supabase_user_id = claims.get("sub")
    email = claims.get("email")

    if not supabase_user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = get_user_by_supabase_user_id(supabase_user_id, session)
    if user is None:
        user = get_user_by_email(email, session)
        if user and not user.supabase_user_id:
            user.supabase_user_id = supabase_user_id
            user.updated_at = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)

    if user is None:
        username = _extract_username(claims, email, session)
        user_type = UserType.ADMIN if is_first_user(session) else UserType.USER
        user = create_user(
            email=email,
            session=session,
            username=username,
            password=None,
            supabase_user_id=supabase_user_id,
            user_type=user_type,
        )
    else:
        should_update = False
        if user.email != email:
            user.email = email
            should_update = True
        if not user.supabase_user_id:
            user.supabase_user_id = supabase_user_id
            should_update = True
        if should_update:
            user.updated_at = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)

    if user.is_deleted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    return user


def update_last_login(session: Session, user: User) -> User:
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_admin_headers() -> dict[str, str]:
    _require_supabase_settings()
    assert settings.SUPABASE_SERVICE_ROLE_KEY is not None
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def create_supabase_auth_user(*, email: str, password: str, username: Optional[str]) -> dict[str, Any]:
    _require_supabase_settings()
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"username": username} if username else {},
    }
    response = httpx.post(
        f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users",
        headers=get_admin_headers(),
        json=payload,
        timeout=15.0,
    )
    if response.status_code >= 400:
        logger.error("Supabase create user failed: %s", response.text)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create Supabase auth user")
    return response.json()


def set_supabase_user_ban_state(supabase_user_id: str, *, banned: bool) -> None:
    _require_supabase_settings()
    payload = {"ban_duration": "876000h" if banned else "none"}
    response = httpx.put(
        f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{supabase_user_id}",
        headers=get_admin_headers(),
        json=payload,
        timeout=15.0,
    )
    if response.status_code >= 400:
        logger.error("Supabase ban/unban failed for %s: %s", supabase_user_id, response.text)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update Supabase auth user state")

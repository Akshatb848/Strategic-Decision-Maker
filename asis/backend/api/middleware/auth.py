"""
ASIS v3.0 — JWT + API key authentication middleware.

Provides:
  get_current_user  — HTTPBearer JWT dependency; extracts user_id and tenant_id.
  verify_api_key    — X-ASIS-Key header dependency (bcrypt hash check); returns tenant_id.
  require_role      — RBAC dependency factory; raises 403 if caller's role is insufficient.

Both get_current_user and verify_api_key populate a CurrentUser context object
that downstream route handlers can Depend on.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...config import get_logger, get_settings
from ...db import ApiKey, User, UserRole, get_db

settings = get_settings()
logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Current user context ──────────────────────────────────────────────────────


@dataclass
class CurrentUser:
    """Auth context injected into route handlers via Depends(get_current_user)."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole
    auth_method: str  # "jwt" | "api_key"


# ── JWT helpers ───────────────────────────────────────────────────────────────


def _decode_jwt(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── JWT dependency ─────────────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    FastAPI dependency: validates Bearer JWT and returns a CurrentUser.

    Expected JWT payload:
      sub       — user UUID
      tenant_id — tenant UUID
      role      — user role string
      exp       — expiry timestamp
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_jwt(credentials.credentials)

    # Extract subject (user_id)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub",
        )
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        ) from exc

    # Extract tenant_id from token (preferred) or fetch from DB
    tenant_id_str = payload.get("tenant_id")
    if tenant_id_str:
        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant ID in token",
            ) from exc
    else:
        # Fallback: load user from DB to get tenant_id
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        tenant_id = user.tenant_id

    # Extract role
    role_str = payload.get("role", UserRole.ANALYST.value)
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.ANALYST

    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        auth_method="jwt",
    )


# ── API key dependency ─────────────────────────────────────────────────────────


async def verify_api_key(
    x_asis_key: str | None = Header(default=None, alias="X-ASIS-Key"),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    FastAPI dependency: validates X-ASIS-Key header against bcrypt hash in DB.

    API keys are tenant-scoped machine-to-machine credentials (used by n8n).
    Returns a CurrentUser with role=ANALYST and the owning tenant_id.
    """
    if not x_asis_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-ASIS-Key header required",
        )

    # Load all active API keys — we must bcrypt-check each
    result = await db.execute(
        select(ApiKey).where(ApiKey.is_active == True)  # noqa: E712
    )
    api_keys = result.scalars().all()

    matched_key: ApiKey | None = None
    for api_key in api_keys:
        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.now(tz=timezone.utc):
            continue
        try:
            if bcrypt.checkpw(
                x_asis_key.encode(),
                api_key.key_hash.encode(),
            ):
                matched_key = api_key
                break
        except Exception:
            continue

    if not matched_key:
        logger.warning("api_key_auth_failed", key_prefix=x_asis_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    # Update last_used_at (fire-and-forget — we do not block on this)
    try:
        matched_key.last_used_at = datetime.now(tz=timezone.utc)
        await db.commit()
    except Exception:
        pass

    logger.info(
        "api_key_authenticated",
        key_label=matched_key.label,
        tenant_id=str(matched_key.tenant_id),
    )

    return CurrentUser(
        user_id=uuid.uuid4(),  # synthetic user_id for API key auth
        tenant_id=matched_key.tenant_id,
        role=UserRole.ANALYST,
        auth_method="api_key",
    )


# ── RBAC factory ───────────────────────────────────────────────────────────────

_ROLE_HIERARCHY = {
    UserRole.VIEWER: 0,
    UserRole.ANALYST: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPERADMIN: 3,
}


def require_role(required_role: UserRole) -> Callable:
    """
    Dependency factory for RBAC.

    Usage::

        @router.delete("/admin/reset", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_reset(...): ...
    """

    async def _check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        caller_level = _ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = _ROLE_HIERARCHY.get(required_role, 99)
        if caller_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{required_role.value}' — caller has '{current_user.role.value}'",
            )
        return current_user

    return _check_role

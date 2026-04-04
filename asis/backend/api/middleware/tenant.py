"""
ASIS v3.0 — Multi-tenant isolation middleware.

Provides:
  get_tenant_id — FastAPI dependency that resolves the active tenant ID
                  from JWT payload or X-Tenant-ID header, then sets
                  app.current_tenant_id on the database connection via
                  SET LOCAL so PostgreSQL Row-Level Security can enforce
                  tenant isolation.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_logger, get_settings
from ...db.session import get_db

settings = get_settings()
logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_tenant_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    FastAPI dependency: resolves the active tenant ID.

    Resolution order:
    1. JWT payload ``tenant_id`` claim (preferred — set during login)
    2. ``X-Tenant-ID`` request header (used by internal services / n8n)
    3. settings.default_tenant_id (fallback for single-tenant deployments)

    After resolving the tenant_id, this dependency executes::

        SET LOCAL app.current_tenant_id = '<tenant_id>';

    on the active database connection. This activates PostgreSQL RLS policies
    defined in db/models.py so every query is automatically scoped to the tenant.
    """
    tenant_id: str = settings.default_tenant_id

    # 1. Try JWT payload first
    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret.get_secret_value(),
                algorithms=[settings.jwt_algorithm],
            )
            jwt_tenant = payload.get("tenant_id")
            if jwt_tenant:
                tenant_id = str(jwt_tenant)
        except JWTError:
            pass  # Fall through to header / default

    # 2. Header override (only if JWT didn't provide one)
    if tenant_id == settings.default_tenant_id and x_tenant_id:
        tenant_id = x_tenant_id.strip()

    # Validate that tenant_id looks reasonable
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine tenant identity",
        )

    # 3. Set PostgreSQL session variable for RLS
    try:
        await db.execute(
            text("SET LOCAL app.current_tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        logger.debug("tenant_context_set", tenant_id=tenant_id)
    except Exception as exc:
        logger.warning("tenant_rls_set_failed", tenant_id=tenant_id, error=str(exc))
        # Non-fatal in dev/test environments without RLS enabled

    return tenant_id


async def bypass_rls(db: AsyncSession) -> None:
    """
    Elevate the current DB connection to bypass RLS.

    Used by admin/superadmin endpoints that must query across tenants.
    Must be called early in the request handler before any queries.
    """
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))

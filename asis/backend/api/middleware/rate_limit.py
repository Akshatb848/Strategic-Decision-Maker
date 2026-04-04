"""
ASIS v3.0 — slowapi rate limiter setup.

Usage in main.py::

    from .middleware.rate_limit import limiter, rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

Usage on individual routes::

    from .middleware.rate_limit import limiter

    @router.post("/analysis")
    @limiter.limit("10/minute")
    async def create_analysis(request: Request, ...):
        ...
"""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ...config import get_settings

settings = get_settings()

# ── Limiter singleton ──────────────────────────────────────────────────────────
# Uses Redis/Memorystore as the storage backend for distributed rate limiting.
# Falls back to in-memory if Redis is unavailable (development mode).

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


# ── Custom rate-limit exceeded handler ────────────────────────────────────────


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Return a structured JSON 429 response instead of the default plain-text one.
    Matches the ASIS error response format used by all other exception handlers.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )

"""
FastAPI application entrypoint for ASIS backend.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import configure_logging, get_settings
from ..db.session import dispose_db, init_db
from .routes import analysis_router, auth_router, health_router, reports_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.environment != "development",
    )
    if settings.environment == "development":
        await init_db()
    yield
    await dispose_db()


def create_app() -> FastAPI:
    """Factory function: create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "ASIS — Autonomous Strategic Intelligence System. "
            "Multi-agent AI platform for enterprise strategic decision intelligence."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ───────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────────────────────
    prefix = settings.api_prefix

    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(analysis_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)

    return app


# WSGI/ASGI entrypoint
app = create_app()

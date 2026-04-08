"""
ASIS v3.0 — FastAPI application entrypoint.

Lifecycle:
  startup  → configure_logging, setup_otel (conditional), init_db (non-prod)
  shutdown → dispose_db

Routers:
  /v1/health, /v1/auth, /v1/analysis, /v1/reports,
  /v1/webhooks, /v1/knowledge, /v1/evaluation

Security:
  - slowapi rate limiter (Memorystore/Redis backend)
  - OpenTelemetry FastAPI instrumentation (settings.otel_enabled)
  - HTTPBearer security scheme advertised in OpenAPI
  - Structured JSON exception handlers (404 / 422 / 500)
"""

from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import configure_logging, get_logger, get_settings
from ..db.session import dispose_db, init_db, run_schema_migrations
from .routes import analysis_router, auth_router, health_router, reports_router
from .routes.webhooks import router as webhooks_router
from .routes.knowledge import router as knowledge_router
from .routes.evaluation import router as evaluation_router

settings = get_settings()
logger = get_logger(__name__)

# ── Security scheme (advertised in OpenAPI only — enforcement is per-route) ────
_http_bearer = HTTPBearer(auto_error=False)


# ── Lifespan ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    # 1. Logging
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.environment != "development",
    )

    # 2. OpenTelemetry (optional)
    if settings.otel_enabled:
        try:
            from ..config.logging import setup_otel
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            setup_otel(
                service_name=settings.otel_service_name,
                endpoint=settings.otel_exporter_otlp_endpoint,
            )
            FastAPIInstrumentor.instrument_app(app)
            logger.info("otel_instrumentation_enabled", service=settings.otel_service_name)
        except ImportError:
            logger.warning("otel_packages_not_installed")

    # 3. Database — create tables (non-production) + always run idempotent migrations
    if settings.environment != "production":
        try:
            await init_db()
            logger.info("db_tables_initialised", environment=settings.environment)
        except Exception as exc:
            logger.warning("db_init_skipped", error=str(exc))

    try:
        await run_schema_migrations()
        logger.info("db_schema_migrations_complete")
    except Exception as exc:
        logger.warning("db_schema_migrations_skipped", error=str(exc))

    # 4. Warn loudly if LLM key is missing — agents will 401 silently otherwise
    llm_key = settings.llm_api_key.get_secret_value()
    anthropic_key = settings.anthropic_api_key.get_secret_value()
    if not llm_key and not anthropic_key:
        logger.error(
            "llm_api_key_missing",
            message=(
                "CRITICAL: LLM_API_KEY is not set. "
                "All agent LLM calls will fail with 401. "
                "Set LLM_API_KEY=gsk_... (Groq) in your .env file and restart."
            ),
        )
    else:
        key_preview = (llm_key or anthropic_key)[:8] + "..."
        logger.info("llm_api_key_present", key_preview=key_preview, base_url=settings.llm_base_url)

    logger.info(
        "asis_started",
        version=settings.app_version,
        environment=settings.environment,
    )

    yield

    # 4. Teardown
    await dispose_db()
    logger.info("asis_shutdown")


# ── App factory ────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Factory: create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "ASIS v3.0 — Autonomous Strategic Intelligence System. "
            "Multi-agent AI platform for enterprise strategic decision intelligence. "
            "Implements a LangGraph pipeline with OpenTelemetry, Langfuse, "
            "Qdrant RAG, Mem0 episodic memory, and a dissertation evaluation framework."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Rate limiting (in-memory — avoids blocking the async event loop) ─────────
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Analysis-Id", "X-Request-Id"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    prefix = settings.api_prefix  # "/v1"

    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(analysis_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(webhooks_router, prefix=prefix)
    app.include_router(knowledge_router, prefix=prefix)
    app.include_router(evaluation_router, prefix=prefix)

    # ── Exception handlers ─────────────────────────────────────────────────────
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": "The requested resource was not found.",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(422)
    async def validation_error_handler(request: Request, exc: Any) -> JSONResponse:
        errors: list[Any] = []
        if hasattr(exc, "errors"):
            try:
                errors = exc.errors()
            except Exception:
                errors = [{"msg": str(exc)}]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request body failed validation.",
                "details": errors,
            },
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Any) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id", "unknown")
        logger.error(
            "unhandled_exception",
            path=str(request.url.path),
            request_id=request_id,
            exc=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again.",
                "request_id": request_id,
            },
        )

    # ── Custom OpenAPI (adds Bearer security scheme) ───────────────────────────
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {})
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-ASIS-Key",
            },
        }
        schema["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


# ── ASGI entrypoint ────────────────────────────────────────────────────────────
app = create_app()

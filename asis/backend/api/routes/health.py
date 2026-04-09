"""
GET /v1/health — comprehensive system health check.

Checks:
  - database  : SELECT 1 via AsyncSession
  - redis      : PING via aioredis
  - qdrant     : GET /healthz via QdrantStore.health_check()
  - litellm    : GET {litellm_proxy_url}/health
  - langfuse   : GET {langfuse_host}/api/public/health
  - celery     : celery inspect ping
  - agents     : dict — all "ready" when pipeline modules load cleanly

No authentication required (used by Docker / Railway / GCP health probes).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ...config import get_logger, get_settings
from ...db.session import AsyncSessionLocal
from ...memory.qdrant_store import QdrantStore
from ..schemas import HealthResponse

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)

_AGENT_NAMES = [
    "orchestrator",
    "market_intelligence",
    "risk_assessment",
    "financial_reasoning",
    "competitor_analysis",
    "synthesis",
]


async def _check_database() -> str:
    """Return 'ok', 'unavailable', or 'error'."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except OperationalError:
        return "unavailable"
    except Exception as exc:
        logger.warning("health_db_error", error=str(exc))
        return "error"


async def _check_redis() -> str:
    """Return 'ok' or 'unavailable'."""
    try:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]

        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:
        logger.warning("health_redis_error", error=str(exc))
        return "unavailable"


async def _check_qdrant() -> str:
    """Return 'ok' or 'unavailable'."""
    try:
        store = QdrantStore()
        healthy = await store.health_check()
        return "ok" if healthy else "unavailable"
    except Exception as exc:
        logger.warning("health_qdrant_error", error=str(exc))
        return "unavailable"


async def _check_litellm() -> str:
    """Return 'ok', 'disabled', or 'unavailable'. LiteLLM is optional."""
    # LiteLLM proxy is only used when explicitly configured; skip by default.
    proxy = settings.litellm_proxy_url
    if not proxy or "localhost:4000" in proxy:
        return "disabled"
    try:
        url = f"{proxy.rstrip('/')}/health"
        timeout = httpx.Timeout(connect=2.0, read=3.0, write=2.0, pool=1.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {settings.litellm_master_key.get_secret_value()}"},
            )
            return "ok" if resp.status_code < 500 else "unavailable"
    except Exception:
        return "unavailable"


async def _check_langfuse() -> str:
    """Return 'ok' or 'unavailable'."""
    if not settings.langfuse_enabled:
        return "disabled"
    try:
        url = f"{settings.langfuse_host.rstrip('/')}/api/public/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code < 500:
                return "ok"
            return "unavailable"
    except Exception as exc:
        logger.warning("health_langfuse_error", error=str(exc))
        return "unavailable"


async def _check_celery() -> str:
    """Return 'ok' or 'unavailable'. Celery inspect with hard 4s wall-clock limit."""
    try:
        from celery import Celery  # type: ignore[import-untyped]

        celery_app = Celery(broker=settings.celery_broker_url)

        def _ping() -> Any:
            inspect = celery_app.control.inspect(timeout=2.0)
            return inspect.ping()

        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _ping),
            timeout=4.0,
        )
        return "ok" if result else "unavailable"
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("health_celery_error", error=str(exc)[:60])
        return "unavailable"


def _check_agents() -> dict[str, str]:
    """
    Verify each agent module is importable and returns 'ready'.
    Returns dict of agent_name → 'ready' | 'error'.
    """
    statuses: dict[str, str] = {}
    try:
        from ...agents.orchestrator import OrchestratorAgent  # noqa: F401
        from ...agents.market_intelligence import MarketIntelligenceAgent  # noqa: F401
        from ...agents.risk_assessment import RiskAssessmentAgent  # noqa: F401
        from ...agents.financial_reasoning import FinancialReasoningAgent  # noqa: F401
        from ...agents.competitor_analysis import CompetitorAnalysisAgent  # noqa: F401
        from ...agents.synthesis import SynthesisAgent  # noqa: F401
        for name in _AGENT_NAMES:
            statuses[name] = "ready"
    except Exception as exc:
        logger.error("health_agents_import_error", error=str(exc))
        for name in _AGENT_NAMES:
            statuses.setdefault(name, "error")
    return statuses


async def _check_llm() -> str:
    """
    Verify the LLM API key is set and the endpoint responds.
    Uses a 5s connect + 5s read timeout so the entire health check
    stays well under Docker's healthcheck timeout limit.
    Returns 'ok' | 'auth_error' | 'no_api_key' | 'rate_limited' | 'unavailable'.
    """
    key = settings.llm_api_key.get_secret_value()
    if not key:
        key = settings.anthropic_api_key.get_secret_value()
    if not key:
        logger.error(
            "health_llm_no_key",
            message="LLM_API_KEY is not set — add LLM_API_KEY=gsk_... to .env",
        )
        return "no_api_key"
    try:
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.claude_haiku_model,
            "max_tokens": 1,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": "hi"}],
        }
        # Generous timeout: GCP VMs can have slow first-connect to external APIs.
        # Still well within Docker's 30s health check timeout.
        timeout = httpx.Timeout(connect=10.0, read=15.0, write=5.0, pool=2.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code == 401:
            logger.error("health_llm_auth_error", status=401)
            return "auth_error"
        if resp.status_code == 429:
            return "rate_limited"
        if resp.is_success:
            return "ok"
        logger.warning("health_llm_error", status=resp.status_code)
        return "unavailable"
    except Exception as exc:
        logger.warning("health_llm_error", error=str(exc)[:80])
        return "unavailable"


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="System health check",
    description=(
        "Returns health status of all system components. "
        "No authentication required. Used by Docker HEALTHCHECK and load-balancer probes."
    ),
)
async def health_check() -> HealthResponse:
    """Comprehensive health check — runs all component checks concurrently."""
    (
        db_status, redis_status, qdrant_status,
        litellm_status, langfuse_status, celery_status, llm_status,
    ) = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_qdrant(),
        _check_litellm(),
        _check_langfuse(),
        _check_celery(),
        _check_llm(),
        return_exceptions=False,
    )

    agent_statuses = _check_agents()

    # Overall status: "ok" only if db, redis, and LLM are all ok.
    # LLM failure means analysis pipeline cannot produce output.
    critical_ok = db_status == "ok" and redis_status == "ok"
    llm_ok = llm_status in ("ok", "rate_limited")
    agents_ok = all(v == "ready" for v in agent_statuses.values())

    if critical_ok and llm_ok and agents_ok:
        overall = "ok"
    elif db_status in ("unavailable", "error"):
        overall = "down"
    elif not llm_ok:
        overall = "degraded"  # running but analysis will fail
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
        qdrant=qdrant_status,
        litellm=litellm_status,
        langfuse=langfuse_status,
        celery=celery_status,
        llm=llm_status,
        agents=agent_statuses,
    )

"""
GET /api/v1/health — system status endpoint (no auth required).
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ...config import get_settings
from ...db.session import AsyncSessionLocal
from ..schemas import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Return system health status. Used by Docker health checks and Railway."""
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except OperationalError:
        db_status = "unavailable"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        agents={
            "orchestrator": "ready",
            "market_intelligence": "ready",
            "risk_assessment": "ready",
            "financial_reasoning": "ready",
            "competitor_analysis": "ready",
            "synthesis": "ready",
        },
    )

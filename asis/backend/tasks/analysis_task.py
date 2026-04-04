"""
ASIS v3.0 — Celery task for running the full LangGraph analysis pipeline.

Wraps the async LangGraph pipeline in a synchronous Celery task, persists
status to the Analysis DB record, and returns the strategic_brief dict.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from asis.backend.tasks.celery_app import celery_app
from asis.backend.config.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="asis.run_analysis",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
    track_started=True,
)
def run_analysis_task(
    self,
    analysis_id: str,
    state_dict: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """
    Execute the ASIS LangGraph pipeline for a given analysis request.

    Updates the Analysis DB record from PENDING → RUNNING on start, then
    COMPLETED with the strategic_brief on success, or FAILED with an error
    message on failure.

    Parameters
    ----------
    analysis_id : str
        UUID string of the Analysis record to update.
    state_dict : dict
        Initial AgentState dict (must contain at minimum ``query`` and
        ``company_context``).
    tenant_id : str
        Tenant identifier injected into state for multi-tenant isolation.

    Returns
    -------
    dict
        The ``strategic_brief`` dict from the final pipeline state.
    """
    logger.info(
        "analysis_task_started",
        analysis_id=analysis_id,
        tenant_id=tenant_id,
        task_id=self.request.id,
    )

    return asyncio.run(
        _run_pipeline(self, analysis_id, state_dict, tenant_id)
    )


async def _run_pipeline(
    task: Any,
    analysis_id: str,
    state_dict: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """
    Async implementation — runs inside asyncio.run() from the Celery worker.
    Updates DB status throughout execution.
    """
    from asis.backend.graph.asis_graph import asis_graph
    from asis.backend.db.session import AsyncSessionLocal
    from asis.backend.db.models import Analysis, AnalysisStatus

    started_at = datetime.now(tz=timezone.utc)

    # ── Mark RUNNING ──────────────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        try:
            analysis = await session.get(Analysis, uuid.UUID(analysis_id))
            if analysis is not None:
                analysis.status = AnalysisStatus.RUNNING
                await session.commit()
        except Exception as exc:
            logger.warning(
                "analysis_task_status_update_failed",
                analysis_id=analysis_id,
                status="RUNNING",
                error=str(exc),
            )

    # ── Build initial state ───────────────────────────────────────────────────
    initial_state = {
        **state_dict,
        "analysis_id": analysis_id,
        "tenant_id": tenant_id,
        "errors": state_dict.get("errors", []),
        "metadata": state_dict.get("metadata", {}),
    }

    # ── Invoke the LangGraph pipeline ─────────────────────────────────────────
    try:
        config = {"configurable": {"thread_id": analysis_id}}
        final_state: dict[str, Any] = await asis_graph.ainvoke(
            initial_state, config=config
        )
        strategic_brief: dict[str, Any] = final_state.get("strategic_brief") or {}

        completed_at = datetime.now(tz=timezone.utc)
        execution_time_ms = int(
            (completed_at - started_at).total_seconds() * 1000
        )

        logger.info(
            "analysis_task_completed",
            analysis_id=analysis_id,
            tenant_id=tenant_id,
            execution_time_ms=execution_time_ms,
        )

        # ── Mark COMPLETED ─────────────────────────────────────────────────────
        async with AsyncSessionLocal() as session:
            try:
                analysis = await session.get(Analysis, uuid.UUID(analysis_id))
                if analysis is not None:
                    analysis.status = AnalysisStatus.COMPLETED
                    analysis.completed_at = completed_at
                    analysis.execution_time_ms = execution_time_ms
                    await session.commit()
            except Exception as exc:
                logger.warning(
                    "analysis_task_status_update_failed",
                    analysis_id=analysis_id,
                    status="COMPLETED",
                    error=str(exc),
                )

        return strategic_brief

    except Exception as exc:
        completed_at = datetime.now(tz=timezone.utc)
        execution_time_ms = int(
            (completed_at - started_at).total_seconds() * 1000
        )
        error_message = str(exc)

        logger.error(
            "analysis_task_failed",
            analysis_id=analysis_id,
            tenant_id=tenant_id,
            error=error_message,
            execution_time_ms=execution_time_ms,
        )

        # ── Mark FAILED ────────────────────────────────────────────────────────
        async with AsyncSessionLocal() as session:
            try:
                analysis = await session.get(Analysis, uuid.UUID(analysis_id))
                if analysis is not None:
                    analysis.status = AnalysisStatus.FAILED
                    analysis.completed_at = completed_at
                    analysis.execution_time_ms = execution_time_ms
                    analysis.error_message = error_message
                    await session.commit()
            except Exception as db_exc:
                logger.warning(
                    "analysis_task_status_update_failed",
                    analysis_id=analysis_id,
                    status="FAILED",
                    error=str(db_exc),
                )

        # Retry the task if retries remain; otherwise re-raise for Celery to record
        raise task.retry(exc=exc) if task.request.retries < task.max_retries else exc

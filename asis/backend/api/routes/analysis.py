"""
POST /v1/analysis     — creates Analysis record, returns StreamingResponse (SSE).
GET  /v1/analysis/{id} — returns AnalysisDetail.
GET  /v1/analysis/{id}/stream — SSE endpoint for live streaming via asyncio.Queue.

SSE event types:
  agent_start      — agent begins execution
  agent_complete   — agent finishes with duration_ms
  agent_error      — non-fatal agent failure
  analysis_complete — final strategic_brief JSON
  error            — fatal pipeline error
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...config import get_logger, get_settings
from ...db import (
    Analysis,
    AnalysisStatus,
    AgentRun,
    AgentStatus,
    Report,
    get_db,
)
from ...db.session import AsyncSessionLocal
from ...graph.asis_graph import asis_graph
from ...graph.state import AgentState
from ..auth import get_current_user_id, get_current_user_id_sse
from ..schemas import (
    AnalysisDetail,
    AgentRunSummary,
    CreateAnalysisRequest,
)

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)

# Single-tenant deployment: all records belong to the default tenant.
_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_AGENT_NAMES = [
    "orchestrator",
    "market_intelligence",
    "risk_assessment",
    "financial_reasoning",
    "competitor_analysis",
    "synthesis",
]

# ── Module-level registries ────────────────────────────────────────────────────
# SSE queues: analysis_id → asyncio.Queue for live event delivery.
_live_queues: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}

# Background task store — CRITICAL: event loop holds only weak refs to Tasks.
# Without a strong reference here, the GC can collect the task mid-execution.
# See: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_running_tasks: set[asyncio.Task] = set()


# ── POST /analysis ─────────────────────────────────────────────────────────────


@router.post(
    "/analysis",
    tags=["Analysis"],
    summary="Trigger ASIS multi-agent pipeline",
    response_description="Server-Sent Events stream of agent progress + final brief",
)
async def create_analysis(
    request: CreateAnalysisRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Trigger the full ASIS pipeline for the given strategic query.

    Returns a Server-Sent Events stream:
      - ``agent_start``      — agent begins execution
      - ``agent_complete``   — agent finishes with duration_ms
      - ``agent_error``      — agent failed (non-fatal, pipeline continues)
      - ``analysis_complete``— final StrategicBrief JSON
      - ``error``            — fatal pipeline error
    """
    # Create analysis record
    analysis = Analysis(
        tenant_id=_DEFAULT_TENANT_ID,
        user_id=user_id,
        query=request.query,
        company_context=request.company_context.model_dump(),
        options=request.options.model_dump(),
        status=AnalysisStatus.RUNNING,
    )
    db.add(analysis)
    await db.flush()
    analysis_id = str(analysis.id)

    # Pre-create agent run records (idle state)
    for name in _AGENT_NAMES:
        db.add(AgentRun(analysis_id=analysis.id, agent_name=name, tenant_id=_DEFAULT_TENANT_ID))
    await db.commit()

    # Create SSE queue and register it before starting the graph
    sse_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    _live_queues[analysis_id] = sse_queue

    async def sse_callback(event_type: str, payload: dict[str, Any]) -> None:
        await sse_queue.put({"event": event_type, "data": payload})

    initial_state: AgentState = {
        "query": request.query,
        "company_context": request.company_context.model_dump(),
        "options": request.options.model_dump(),
        "analysis_id": analysis_id,
        "errors": [],
        "metadata": {
            "sse_callback": sse_callback,
            "started_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    }

    # Launch graph in independent background task — persists results regardless
    # of whether the SSE connection stays open or the client navigates away.
    # Store strong reference in _running_tasks to prevent GC mid-execution.
    start_time = int(time.time() * 1000)
    task = asyncio.create_task(
        _run_graph_and_persist(analysis_id, initial_state, sse_queue, start_time),
        name=f"asis-graph-{analysis_id[:8]}",
    )
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    return StreamingResponse(
        _drain_sse_queue(analysis_id, sse_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Analysis-Id": analysis_id,
        },
    )


# ── Graph runner (independent of SSE connection) ───────────────────────────────


async def _run_graph_and_persist(
    analysis_id: str,
    initial_state: AgentState,
    sse_queue: asyncio.Queue[dict[str, Any] | None],
    start_time: int,
) -> None:
    """
    Run the ASIS graph and persist results using a FRESH DB session.

    This task is independent of the SSE generator — it will complete and
    write to the DB even if the client disconnects mid-stream.
    """
    logger.info("graph_task_start", analysis_id=analysis_id)
    try:
        final_state: AgentState = await asis_graph.ainvoke(initial_state)
        duration_ms = int(time.time() * 1000) - start_time

        async with AsyncSessionLocal() as db:
            await _persist_results(analysis_id, final_state, duration_ms, db)

        logger.info("graph_task_complete", analysis_id=analysis_id, duration_ms=duration_ms)

        # Notify any connected SSE consumers that we're done
        await sse_queue.put({
            "event": "analysis_complete",
            "data": {
                "analysis_id": analysis_id,
                "duration_ms": duration_ms,
                "strategic_brief": final_state.get("strategic_brief"),
                "errors": final_state.get("errors", []),
            },
        })

    except BaseException as exc:
        # Catch ALL exceptions including asyncio.CancelledError so they are logged
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("pipeline_error", analysis_id=analysis_id, error=error_msg)
        try:
            async with AsyncSessionLocal() as db:
                await _mark_failed(analysis_id, error_msg, db)
        except Exception:
            pass
        await sse_queue.put({
            "event": "error",
            "data": {"analysis_id": analysis_id, "message": error_msg},
        })
        if isinstance(exc, asyncio.CancelledError):
            raise  # re-raise so asyncio knows the task was cancelled

    finally:
        # Sentinel: tells the SSE drain loop to close the stream
        await sse_queue.put(None)
        _live_queues.pop(analysis_id, None)


# ── SSE drain generator ────────────────────────────────────────────────────────


async def _drain_sse_queue(
    analysis_id: str,
    queue: asyncio.Queue[dict[str, Any] | None],
) -> AsyncGenerator[str, None]:
    """
    Yield SSE events from the queue. Sends a heartbeat comment every 15 s so
    that proxies and browsers don't close idle connections during Groq backoffs.
    """
    def _fmt(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=15.0)
        except asyncio.TimeoutError:
            # Heartbeat — keeps the connection alive during long LLM backoffs
            yield ": heartbeat\n\n"
            continue

        if item is None:
            # Sentinel from _run_graph_and_persist — pipeline done
            break

        yield _fmt(item["event"], item["data"])


# ── DB helpers ─────────────────────────────────────────────────────────────────


async def _persist_results(
    analysis_id: str,
    state: AgentState,
    duration_ms: int,
    db: AsyncSession,
) -> None:
    """Persist final analysis state to the database."""
    aid = uuid.UUID(analysis_id)

    # ── Step 1: mark analysis COMPLETED (own transaction) ─────────────────────
    try:
        async with db.begin():
            result = await db.execute(select(Analysis).where(Analysis.id == aid))
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = AnalysisStatus.COMPLETED
                analysis.completed_at = datetime.now(tz=timezone.utc)
                analysis.execution_time_ms = duration_ms
    except Exception as exc:
        logger.error("persist_analysis_status_error", analysis_id=analysis_id, error=str(exc), exc_info=True)

    # ── Step 2: update per-agent token counts (own transaction) ───────────────
    try:
        async with db.begin():
            metadata = state.get("metadata", {})
            token_usage = metadata.get("token_usage", {})
            for agent_name in _AGENT_NAMES:
                run_result = await db.execute(
                    select(AgentRun).where(
                        AgentRun.analysis_id == aid,
                        AgentRun.agent_name == agent_name,
                    )
                )
                agent_run = run_result.scalar_one_or_none()
                if agent_run:
                    agent_run.status = AgentStatus.COMPLETED
                    agent_run.tokens_used = token_usage.get(agent_name, 0)
    except Exception as exc:
        logger.error("persist_agent_runs_error", analysis_id=analysis_id, error=str(exc), exc_info=True)

    # ── Step 3: create report record (own transaction) ────────────────────────
    brief = state.get("strategic_brief")
    if not brief:
        logger.error(
            "persist_results_no_brief",
            analysis_id=analysis_id,
            state_keys=list(state.keys()),
        )
        return

    try:
        async with db.begin():
            # Check if a report already exists (idempotency)
            existing_report = await db.execute(
                select(Report).where(Report.analysis_id == aid)
            )
            if existing_report.scalar_one_or_none():
                logger.info("persist_results_report_exists", analysis_id=analysis_id)
                return

            report = Report(
                analysis_id=aid,
                tenant_id=_DEFAULT_TENANT_ID,
                strategic_brief=brief,
                confidence_score=brief.get("overall_confidence"),
                data_quality_score=brief.get("overall_confidence"),
                sources_count=0,
            )
            db.add(report)
        logger.info(
            "persist_results_report_saved",
            analysis_id=analysis_id,
            confidence=brief.get("overall_confidence"),
        )
    except Exception as exc:
        logger.error(
            "persist_results_error",
            analysis_id=analysis_id,
            error=str(exc),
            exc_info=True,
        )
        # Fallback: try raw SQL insert to bypass any ORM column mapping issues
        try:
            async with db.begin():
                import json as _json
                await db.execute(
                    text(
                        """
                        INSERT INTO reports
                            (id, analysis_id, strategic_brief, confidence_score,
                             data_quality_score, sources_count)
                        VALUES
                            (:id, :analysis_id, :brief::jsonb, :confidence,
                             :confidence, 0)
                        ON CONFLICT (analysis_id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "analysis_id": str(aid),
                        "brief": _json.dumps(brief),
                        "confidence": brief.get("overall_confidence"),
                    },
                )
            logger.info("persist_results_fallback_insert_ok", analysis_id=analysis_id)
        except Exception as fallback_exc:
            logger.error(
                "persist_results_fallback_error",
                analysis_id=analysis_id,
                error=str(fallback_exc),
                exc_info=True,
            )


async def _mark_failed(analysis_id: str, error_msg: str, db: AsyncSession) -> None:
    """Mark analysis as FAILED in the database."""
    try:
        async with db.begin():
            result = await db.execute(
                select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
            )
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = AnalysisStatus.FAILED
                analysis.completed_at = datetime.now(tz=timezone.utc)
    except Exception as exc:
        logger.error("mark_failed_error", analysis_id=analysis_id, error=str(exc))


# ── GET /analysis/{id} ─────────────────────────────────────────────────────────


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisDetail,
    tags=["Analysis"],
    summary="Retrieve analysis by ID",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetail:
    """Retrieve a specific analysis by ID. Enforces ownership check."""
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    runs_result = await db.execute(
        select(AgentRun).where(AgentRun.analysis_id == analysis_id)
    )
    agent_runs = runs_result.scalars().all()

    report_result = await db.execute(
        select(Report).where(Report.analysis_id == analysis_id)
    )
    report = report_result.scalar_one_or_none()

    return AnalysisDetail(
        id=str(analysis.id),
        query=analysis.query,
        status=analysis.status.value,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        execution_time_ms=analysis.execution_time_ms,
        confidence_score=report.confidence_score if report else None,
        data_quality_score=report.data_quality_score if report else None,
        company_context=analysis.company_context,
        agent_runs=[
            AgentRunSummary(
                agent_name=r.agent_name,
                status=r.status.value,
                tokens_used=r.tokens_used,
                duration_ms=r.duration_ms,
                error_message=r.error_message,
            )
            for r in agent_runs
        ],
        strategic_brief=report.strategic_brief if report else None,
    )


# ── GET /analysis/{id}/stream ──────────────────────────────────────────────────


@router.get(
    "/analysis/{analysis_id}/stream",
    tags=["Analysis"],
    summary="SSE stream for live analysis progress",
    response_description="Server-Sent Events — live queue then DB poll until done",
)
async def stream_analysis(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id_sse),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE endpoint for monitoring a previously created analysis.
    If the graph is still running, drains the live event queue.
    Otherwise polls the database until the analysis reaches a terminal state.
    """
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    aid = str(analysis_id)

    # If the live queue exists (graph still running), tap into it
    live_queue = _live_queues.get(aid)
    if live_queue is not None:
        return StreamingResponse(
            _drain_sse_queue(aid, live_queue),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Otherwise fall back to DB polling
    return StreamingResponse(
        _poll_stream(aid, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _poll_stream(
    analysis_id: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Poll DB for analysis status and stream updates via SSE."""
    terminal_states = {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}
    last_status: str | None = None
    poll_interval = 2.0
    max_polls = 300  # 10 minutes max

    for _ in range(max_polls):
        result = await db.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            yield f"event: error\ndata: {json.dumps({'message': 'Analysis not found'})}\n\n"
            return

        current_status = analysis.status.value
        if current_status != last_status:
            yield f"event: status_update\ndata: {json.dumps({'analysis_id': analysis_id, 'status': current_status})}\n\n"
            last_status = current_status

        if analysis.status in terminal_states:
            report_result = await db.execute(
                select(Report).where(Report.analysis_id == uuid.UUID(analysis_id))
            )
            report = report_result.scalar_one_or_none()
            event_type = "analysis_complete" if analysis.status == AnalysisStatus.COMPLETED else "error"
            payload: dict[str, Any] = {
                "analysis_id": analysis_id,
                "status": current_status,
                "execution_time_ms": analysis.execution_time_ms,
            }
            if analysis.status == AnalysisStatus.COMPLETED and report:
                payload["strategic_brief"] = report.strategic_brief
            elif analysis.status == AnalysisStatus.FAILED:
                payload["message"] = "Pipeline failed"
            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
            return

        # Heartbeat during polling to keep connection alive
        yield ": heartbeat\n\n"
        await asyncio.sleep(poll_interval)

    yield f"event: error\ndata: {json.dumps({'analysis_id': analysis_id, 'message': 'Stream timeout'})}\n\n"

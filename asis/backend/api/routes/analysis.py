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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from ...graph.asis_graph import asis_graph
from ...graph.state import AgentState
from ..auth import get_current_user_id
from ..schemas import (
    AnalysisDetail,
    AgentRunSummary,
    CreateAnalysisRequest,
)

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
        db.add(AgentRun(analysis_id=analysis.id, agent_name=name))
    await db.commit()

    return StreamingResponse(
        _stream_pipeline(analysis_id, request, user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Analysis-Id": analysis_id,
        },
    )


# ── SSE streaming internals ────────────────────────────────────────────────────


async def _stream_pipeline(
    analysis_id: str,
    request: CreateAnalysisRequest,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Async generator: runs the ASIS graph and yields SSE events."""
    sse_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    start_time = int(time.time() * 1000)

    async def sse_callback(event_type: str, payload: dict[str, Any]) -> None:
        await sse_queue.put({"event": event_type, "data": payload})

    def _format_sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Build initial state — inject sse_callback into metadata so agents can emit events
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

    # Run graph in background; drain SSE queue in foreground
    graph_task = asyncio.create_task(asis_graph.ainvoke(initial_state))

    try:
        while not graph_task.done() or not sse_queue.empty():
            try:
                event_item = sse_queue.get_nowait()
                yield _format_sse(event_item["event"], event_item["data"])
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.05)

        # Graph finished — retrieve final state
        final_state: AgentState = await graph_task
        duration_ms = int(time.time() * 1000) - start_time

        # Persist results to DB
        await _persist_results(analysis_id, final_state, duration_ms, db)

        # Emit final analysis_complete event with strategic_brief
        yield _format_sse(
            "analysis_complete",
            {
                "analysis_id": analysis_id,
                "duration_ms": duration_ms,
                "strategic_brief": final_state.get("strategic_brief"),
                "errors": final_state.get("errors", []),
            },
        )

    except Exception as exc:
        logger.error("pipeline_error", analysis_id=analysis_id, error=str(exc))
        await _mark_failed(analysis_id, str(exc), db)
        yield _format_sse("error", {"analysis_id": analysis_id, "message": str(exc)})


async def _persist_results(
    analysis_id: str,
    state: AgentState,
    duration_ms: int,
    db: AsyncSession,
) -> None:
    """Persist final analysis state to the database."""
    try:
        async with db.begin_nested():
            # Update analysis record
            result = await db.execute(
                select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
            )
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = AnalysisStatus.COMPLETED
                analysis.completed_at = datetime.now(tz=timezone.utc)
                analysis.execution_time_ms = duration_ms

            # Update per-agent run records with token usage
            metadata = state.get("metadata", {})
            token_usage = metadata.get("token_usage", {})
            for agent_name in _AGENT_NAMES:
                run_result = await db.execute(
                    select(AgentRun).where(
                        AgentRun.analysis_id == uuid.UUID(analysis_id),
                        AgentRun.agent_name == agent_name,
                    )
                )
                agent_run = run_result.scalar_one_or_none()
                if agent_run:
                    agent_run.status = AgentStatus.COMPLETED
                    agent_run.tokens_used = token_usage.get(agent_name, 0)

            # Create report record from StrategicBrief
            brief = state.get("strategic_brief")
            if brief:
                report = Report(
                    analysis_id=uuid.UUID(analysis_id),
                    strategic_brief=brief,
                    confidence_score=brief.get("confidence_score"),
                    data_quality_score=brief.get("data_quality_score"),
                    sources_count=len(brief.get("sources", [])),
                )
                db.add(report)

    except Exception as exc:
        logger.error("persist_results_error", analysis_id=analysis_id, error=str(exc))


async def _mark_failed(analysis_id: str, error_msg: str, db: AsyncSession) -> None:
    """Mark analysis as FAILED in the database."""
    try:
        result = await db.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        )
        analysis = result.scalar_one_or_none()
        if analysis:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = error_msg
            analysis.completed_at = datetime.now(tz=timezone.utc)
        await db.commit()
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
    response_description="Server-Sent Events — polls DB until analysis completes",
)
async def stream_analysis(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE endpoint for monitoring a previously created analysis.
    Polls the database and emits status events until the analysis reaches
    a terminal state (completed or failed).
    """
    # Verify the analysis exists and belongs to the caller
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    return StreamingResponse(
        _poll_stream(str(analysis_id), db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Analysis-Id": str(analysis_id),
        },
    )


async def _poll_stream(
    analysis_id: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Poll DB for analysis status and stream updates via SSE."""
    terminal_states = {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}
    last_status: str | None = None
    poll_interval = 1.0  # seconds
    max_polls = 300  # 5 minutes max

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
            # Fetch report for final brief
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
                payload["confidence_score"] = report.confidence_score
            elif analysis.status == AnalysisStatus.FAILED:
                payload["message"] = analysis.error_message or "Pipeline failed"

            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
            return

        await asyncio.sleep(poll_interval)

    yield f"event: error\ndata: {json.dumps({'analysis_id': analysis_id, 'message': 'Stream timeout — analysis still running'})}\n\n"

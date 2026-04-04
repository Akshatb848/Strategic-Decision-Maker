"""
GET /v1/reports                  — paginated list with filters (tenant, date, status, sector).
GET /v1/reports/{id}             — full report detail.
GET /v1/evaluation/export        — CSV export of comparison data for dissertation.
GET /v1/reports/{id}/evaluation  — evaluation scores for a single report.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...config import get_logger, get_settings
from ...db import Analysis, AnalysisStatus, BaselineRun, Report, get_db
from ...evaluation.engine import EvaluationEngine
from ..auth import get_current_user_id
from ..schemas import (
    AnalysisSummary,
    EvaluationResponse,
    PaginatedAnalyses,
    ReportSummary,
)

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)
_eval_engine = EvaluationEngine()


# ── GET /reports ───────────────────────────────────────────────────────────────


@router.get(
    "/reports",
    response_model=PaginatedAnalyses,
    tags=["Reports"],
    summary="List reports with filters",
)
async def list_reports(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by analysis status"),
    tenant_id: str | None = Query(default=None, description="Filter by tenant ID"),
    sector: str | None = Query(default=None, description="Filter by company sector (substring match)"),
    date_from: date | None = Query(default=None, description="Filter analyses created on or after this date"),
    date_to: date | None = Query(default=None, description="Filter analyses created on or before this date"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAnalyses:
    """
    Return paginated list of analyses for the authenticated user.
    Supports filtering by status, sector (within company_context JSON), and date range.
    """
    base_q = select(Analysis).where(Analysis.user_id == user_id)

    # Status filter
    if status_filter:
        try:
            status_enum = AnalysisStatus(status_filter)
            base_q = base_q.where(Analysis.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status values silently

    # Sector filter — JSON field access via SQLAlchemy (PostgreSQL)
    if sector:
        base_q = base_q.where(
            Analysis.company_context["sector"].astext.ilike(f"%{sector}%")
        )

    # Date range filter
    if date_from:
        base_q = base_q.where(
            Analysis.created_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        base_q = base_q.where(
            Analysis.created_at <= datetime.combine(date_to, datetime.max.time())
        )

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    # Paginated items
    items_q = (
        base_q.order_by(Analysis.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await db.execute(items_q)
    analyses = items_result.scalars().all()

    return PaginatedAnalyses(
        items=[
            AnalysisSummary(
                id=a.id,
                query=a.query,
                status=a.status.value,
                created_at=a.created_at,
                completed_at=a.completed_at,
                execution_time_ms=a.execution_time_ms,
            )
            for a in analyses
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /reports/{id} ──────────────────────────────────────────────────────────


@router.get(
    "/reports/{analysis_id}",
    response_model=ReportSummary,
    tags=["Reports"],
    summary="Full report detail",
)
async def get_report(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReportSummary:
    """Return the full StrategicBrief for a completed analysis."""
    # Verify ownership
    analysis_result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
    )
    if not analysis_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )

    report_result = await db.execute(
        select(Report).where(Report.analysis_id == analysis_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found — analysis may still be running",
        )

    return ReportSummary(
        id=report.id,
        analysis_id=report.analysis_id,
        confidence_score=report.confidence_score,
        data_quality_score=report.data_quality_score,
        sources_count=report.sources_count,
        eval_overall_score=report.eval_overall_score,
        created_at=report.created_at,
    )


# ── GET /reports/{id}/evaluation ───────────────────────────────────────────────


@router.get(
    "/reports/{analysis_id}/evaluation",
    response_model=EvaluationResponse,
    tags=["Reports", "Evaluation"],
    summary="Evaluation scores for a report",
)
async def get_evaluation(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Return evaluation scores for a completed analysis, including baseline comparison."""
    # Verify ownership
    analysis_result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )

    report_result = await db.execute(
        select(Report).where(Report.analysis_id == analysis_id)
    )
    report = report_result.scalar_one_or_none()

    baseline_result = await db.execute(
        select(BaselineRun).where(BaselineRun.analysis_id == analysis_id)
    )
    baseline = baseline_result.scalar_one_or_none()

    # Trigger evaluation if scores are missing
    if report and report.eval_overall_score is None:
        scores = await _eval_engine.evaluate(report.strategic_brief, analysis.query)
        report.eval_analytical_depth = scores["analytical_depth"]
        report.eval_factual_accuracy = scores["factual_accuracy"]
        report.eval_contextual_relevance = scores["contextual_relevance"]
        report.eval_actionability = scores["actionability"]
        report.eval_internal_consistency = scores["internal_consistency"]
        report.eval_overall_score = scores["overall_score"]
        await db.commit()

    improvement: float | None = None
    if (
        report
        and report.eval_overall_score is not None
        and baseline
        and baseline.eval_overall_score is not None
    ):
        improvement = round(report.eval_overall_score - baseline.eval_overall_score, 2)

    return EvaluationResponse(
        analysis_id=analysis_id,
        analytical_depth=report.eval_analytical_depth if report else None,
        factual_accuracy=report.eval_factual_accuracy if report else None,
        contextual_relevance=report.eval_contextual_relevance if report else None,
        actionability=report.eval_actionability if report else None,
        internal_consistency=report.eval_internal_consistency if report else None,
        overall_score=report.eval_overall_score if report else None,
        baseline_overall_score=baseline.eval_overall_score if baseline else None,
        improvement_over_baseline=improvement,
    )


# ── GET /evaluation/export ─────────────────────────────────────────────────────


@router.get(
    "/evaluation/export",
    tags=["Evaluation"],
    summary="CSV export of multi-agent vs baseline comparison for dissertation",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "CSV file with per-analysis evaluation scores",
        }
    },
)
async def export_evaluation_csv(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export all evaluation comparison data as CSV.

    Columns:
      analysis_id, query_excerpt, created_at,
      multi_agent_overall, multi_agent_analytical_depth, multi_agent_factual_accuracy,
      multi_agent_contextual_relevance, multi_agent_actionability, multi_agent_internal_consistency,
      multi_agent_execution_ms, multi_agent_confidence,
      baseline_overall, baseline_analytical_depth, baseline_factual_accuracy,
      baseline_contextual_relevance, baseline_actionability, baseline_internal_consistency,
      baseline_execution_ms, delta_overall
    """
    # Fetch all completed analyses for this user
    analyses_result = await db.execute(
        select(Analysis).where(
            Analysis.user_id == user_id,
            Analysis.status == AnalysisStatus.COMPLETED,
        ).order_by(Analysis.created_at.asc())
    )
    analyses = analyses_result.scalars().all()

    output = io.StringIO()
    fieldnames = [
        "analysis_id",
        "query_excerpt",
        "created_at",
        "multi_agent_overall",
        "multi_agent_analytical_depth",
        "multi_agent_factual_accuracy",
        "multi_agent_contextual_relevance",
        "multi_agent_actionability",
        "multi_agent_internal_consistency",
        "multi_agent_execution_ms",
        "multi_agent_confidence",
        "baseline_overall",
        "baseline_analytical_depth",
        "baseline_factual_accuracy",
        "baseline_contextual_relevance",
        "baseline_actionability",
        "baseline_internal_consistency",
        "baseline_execution_ms",
        "delta_overall",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for analysis in analyses:
        # Fetch corresponding report and baseline
        report_result = await db.execute(
            select(Report).where(Report.analysis_id == analysis.id)
        )
        report = report_result.scalar_one_or_none()

        baseline_result = await db.execute(
            select(BaselineRun).where(BaselineRun.analysis_id == analysis.id)
        )
        baseline = baseline_result.scalar_one_or_none()

        delta: Any = ""
        if (
            report
            and report.eval_overall_score is not None
            and baseline
            and baseline.eval_overall_score is not None
        ):
            delta = round(report.eval_overall_score - baseline.eval_overall_score, 4)

        row: dict[str, Any] = {
            "analysis_id": str(analysis.id),
            "query_excerpt": analysis.query[:80],
            "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
            "multi_agent_overall": report.eval_overall_score if report else "",
            "multi_agent_analytical_depth": report.eval_analytical_depth if report else "",
            "multi_agent_factual_accuracy": report.eval_factual_accuracy if report else "",
            "multi_agent_contextual_relevance": report.eval_contextual_relevance if report else "",
            "multi_agent_actionability": report.eval_actionability if report else "",
            "multi_agent_internal_consistency": report.eval_internal_consistency if report else "",
            "multi_agent_execution_ms": analysis.execution_time_ms or "",
            "multi_agent_confidence": report.confidence_score if report else "",
            "baseline_overall": baseline.eval_overall_score if baseline else "",
            "baseline_analytical_depth": baseline.eval_analytical_depth if baseline else "",
            "baseline_factual_accuracy": baseline.eval_factual_accuracy if baseline else "",
            "baseline_contextual_relevance": baseline.eval_contextual_relevance if baseline else "",
            "baseline_actionability": baseline.eval_actionability if baseline else "",
            "baseline_internal_consistency": baseline.eval_internal_consistency if baseline else "",
            "baseline_execution_ms": baseline.duration_ms if baseline else "",
            "delta_overall": delta,
        }
        writer.writerow(row)

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=asis_evaluation_export.csv",
        },
    )

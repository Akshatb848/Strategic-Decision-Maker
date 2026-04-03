"""
GET /api/v1/reports — paginated list of past analyses
GET /api/v1/reports/{id} — full StrategicBrief
GET /api/v1/reports/{id}/evaluation — evaluation scores
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ...db import Analysis, AnalysisStatus, Report, BaselineRun, get_db
from ...evaluation.engine import EvaluationEngine
from ..auth import get_current_user_id
from ..schemas import (
    AnalysisSummary,
    EvaluationResponse,
    PaginatedAnalyses,
    ReportSummary,
)

router = APIRouter()
_eval_engine = EvaluationEngine()


@router.get("/reports", response_model=PaginatedAnalyses, tags=["Reports"])
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAnalyses:
    """Return paginated list of analyses for the authenticated user."""
    base_q = select(Analysis).where(Analysis.user_id == user_id)
    if status_filter:
        try:
            status_enum = AnalysisStatus(status_filter)
            base_q = base_q.where(Analysis.status == status_enum)
        except ValueError:
            pass  # ignore invalid status filter

    count_q = select(func.count()).select_from(base_q.subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

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


@router.get("/reports/{analysis_id}", response_model=ReportSummary, tags=["Reports"])
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    report_result = await db.execute(
        select(Report).where(Report.analysis_id == analysis_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found — analysis may still be running"
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


@router.get(
    "/reports/{analysis_id}/evaluation",
    response_model=EvaluationResponse,
    tags=["Reports", "Evaluation"],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

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
        improvement = round(
            report.eval_overall_score - baseline.eval_overall_score, 2
        )

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

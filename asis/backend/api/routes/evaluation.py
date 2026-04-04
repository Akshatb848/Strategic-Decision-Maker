"""
GET /v1/evaluation/export — CSV export (also exported from reports.py for convenience).
This router exists so evaluation-specific endpoints can grow independently.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...config import get_logger, get_settings
from ...db import Analysis, AnalysisStatus, BaselineRun, Report, get_db
from ...evaluation.engine import EvaluationEngine
from ..auth import get_current_user_id
from ..schemas import EvaluationResponse

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])
settings = get_settings()
logger = get_logger(__name__)
_eval_engine = EvaluationEngine()


@router.get(
    "/{analysis_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation scores for an analysis",
)
async def get_evaluation_scores(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Return all five EvaluationEngine dimension scores for a completed analysis,
    plus the baseline comparison and delta if a SingleAgentBaseline run exists.

    If scores have not yet been computed, they are computed on-demand and persisted.
    """
    # Verify ownership
    analysis_result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )

    if analysis.status not in (AnalysisStatus.COMPLETED,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is in '{analysis.status.value}' state — evaluation requires 'completed'",
        )

    report_result = await db.execute(
        select(Report).where(Report.analysis_id == analysis_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found for this analysis",
        )

    baseline_result = await db.execute(
        select(BaselineRun).where(BaselineRun.analysis_id == analysis_id)
    )
    baseline = baseline_result.scalar_one_or_none()

    # Compute evaluation scores if not yet stored
    if report.eval_overall_score is None:
        logger.info("evaluation_computing_on_demand", analysis_id=str(analysis_id))
        scores = await _eval_engine.evaluate(report.strategic_brief, analysis.query)
        report.eval_analytical_depth = scores["analytical_depth"]
        report.eval_factual_accuracy = scores["factual_accuracy"]
        report.eval_contextual_relevance = scores["contextual_relevance"]
        report.eval_actionability = scores["actionability"]
        report.eval_internal_consistency = scores["internal_consistency"]
        report.eval_overall_score = scores["overall_score"]
        await db.commit()
        logger.info(
            "evaluation_stored",
            analysis_id=str(analysis_id),
            overall_score=report.eval_overall_score,
        )

    improvement: float | None = None
    if (
        report.eval_overall_score is not None
        and baseline
        and baseline.eval_overall_score is not None
    ):
        improvement = round(report.eval_overall_score - baseline.eval_overall_score, 2)

    return EvaluationResponse(
        analysis_id=analysis_id,
        analytical_depth=report.eval_analytical_depth,
        factual_accuracy=report.eval_factual_accuracy,
        contextual_relevance=report.eval_contextual_relevance,
        actionability=report.eval_actionability,
        internal_consistency=report.eval_internal_consistency,
        overall_score=report.eval_overall_score,
        baseline_overall_score=baseline.eval_overall_score if baseline else None,
        improvement_over_baseline=improvement,
    )

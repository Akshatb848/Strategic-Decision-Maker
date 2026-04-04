"""
ASIS v3.0 — Evaluation schemas for EvaluationEngine and dissertation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=20)
    weighted_contribution: float = Field(ge=0.0)


class EvaluationResult(BaseModel):
    analysis_id: str
    report_type: str = Field(description="multi_agent or baseline")
    analytical_depth: DimensionScore
    factual_accuracy: DimensionScore
    contextual_relevance: DimensionScore
    actionability: DimensionScore
    internal_consistency: DimensionScore
    overall_score: float = Field(ge=0.0, le=10.0)
    evaluator_model: str
    evaluation_tokens: int = 0
    evaluated_at: str = ""


class ComparisonResult(BaseModel):
    """Side-by-side multi-agent vs baseline scores for dissertation export."""

    analysis_id: str
    scenario_label: str
    multi_agent_overall: float
    baseline_overall: float
    delta: float
    multi_agent_scores: dict[str, float]
    baseline_scores: dict[str, float]
    multi_agent_tokens: int
    baseline_tokens: int
    multi_agent_duration_ms: int
    baseline_duration_ms: int

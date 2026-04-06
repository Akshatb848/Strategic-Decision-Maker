"""
ASIS v3.0 — Pydantic v2 agent output schemas.
Aligned with MANG6550 Dissertation prompt architecture.
Every agent validates its LLM output against these schemas (2 retries on fail).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Orchestrator ──────────────────────────────────────────────────────────────
# Dissertation: Minto Pyramid + Issue Tree decomposition

class OrchestratorOutput(BaseModel):
    problem_decomposition: list[str] = Field(
        min_length=2,
        description="MECE sub-problems (Minto Pyramid Issue Tree)"
    )
    analytical_framework: str = Field(
        description="Primary strategic framework selected and rationale"
    )
    agent_assignments: dict[str, str] = Field(
        description="agent_name → specific task with scope and output"
    )
    key_hypotheses: list[str] = Field(
        min_length=2,
        description="Falsifiable hypotheses grounded in problem context"
    )
    success_criteria: list[str] = Field(
        min_length=2,
        description="Measurable success criteria with metrics"
    )
    confidence_score: int = Field(ge=0, le=100, default=80)
    strategic_priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    time_horizon: str = "3-5 years"
    dissertation_note: str = Field(
        default="",
        description="One sentence connecting to multi-agent AI theory"
    )
    # Routing field kept for LangGraph graph compatibility (always full_brief)
    query_type: str = Field(default="full_brief")


# Legacy alias — kept so graph routing (task_plan["query_type"]) continues to work
TaskPlan = OrchestratorOutput


# ── Market Intelligence ────────────────────────────────────────────────────────
# Dissertation: PESTLE + Porter's Five Forces

class MarketIntelReport(BaseModel):
    regulatory_landscape: list[str] = Field(
        min_length=2,
        description="Named regulations/standards and their direct operational impact"
    )
    market_signals: list[str] = Field(
        min_length=2,
        description="Quantified or named market trends with source context"
    )
    key_findings: list[str] = Field(
        min_length=2,
        description="Evidence-grounded insights from environmental scan"
    )
    emerging_risks: list[str] = Field(
        default_factory=list,
        description="Named risks with probability and business impact"
    )
    opportunities: list[str] = Field(
        default_factory=list,
        description="Specific strategic opportunities with estimated value"
    )
    methodology: str = Field(default="PESTLE + Porter's Five Forces")
    data_sources: list[str] = Field(default_factory=list)
    confidence_score: int = Field(ge=0, le=100, default=78)
    strategic_implication: str = Field(
        description="Single board-level sentence: what leadership must act on immediately"
    )


# ── Risk Assessment ────────────────────────────────────────────────────────────
# Dissertation: COSO ERM 2017 + ISO 31000 + NIST CSF

class DissertationRiskItem(BaseModel):
    risk: str = Field(description="Specific named risk (not generic)")
    category: str = Field(
        description="Regulatory | Cyber | Operational | Financial | Talent | Reputational | Geopolitical"
    )
    likelihood: Literal["High", "Medium", "Low"]
    impact: Literal["Critical", "High", "Medium", "Low"]
    velocity: Literal["Immediate", "Near-term", "Long-term"]
    severity_score: int = Field(
        ge=0, le=100,
        description="Likelihood × Impact × Velocity normalised to 100"
    )
    owner: str = Field(description="Functional owner e.g. Chief Compliance Officer")
    current_control: str = Field(description="Existing control mechanism")


class RiskReport(BaseModel):
    risk_register: list[DissertationRiskItem] = Field(min_length=2)
    critical_risks: list[str] = Field(
        min_length=1,
        description="Top risks requiring board attention with consequence"
    )
    mitigation_strategies: list[str] = Field(
        min_length=2,
        description="Specific actions with timeline and expected risk reduction %"
    )
    residual_risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_appetite_alignment: str = Field(
        description="Whether current exposure aligns with stated risk appetite"
    )
    framework_used: str = Field(default="COSO ERM 2017 + NIST CSF 2.0")
    confidence_score: int = Field(ge=0, le=100, default=75)
    board_escalation_required: bool
    escalation_rationale: str


# ── Competitor Analysis ────────────────────────────────────────────────────────
# Dissertation: Porter's Generic Strategies + Competitive Intelligence Matrix

class Benchmark(BaseModel):
    dimension: str
    our_score: int = Field(ge=0, le=100)
    industry_avg: int = Field(ge=0, le=100)
    leader_score: int = Field(ge=0, le=100)
    gap_to_leader: int = Field(ge=0, le=100)
    benchmark_source: str


class CompetitorReport(BaseModel):
    competitive_landscape: list[str] = Field(
        min_length=2,
        description="Named competitor insights: specific strategic moves or capabilities"
    )
    benchmarks: list[Benchmark] = Field(
        min_length=2,
        description="Multi-dimensional competitor benchmarks (0-100 scale)"
    )
    competitive_gaps: list[str] = Field(
        min_length=1,
        description="Named dimension, quantified gap, and business consequence"
    )
    differentiators: list[str] = Field(
        min_length=1,
        description="Genuine competitive advantages with evidence"
    )
    strategic_moves: list[str] = Field(
        min_length=2,
        description="Specific actions to close gaps or extend lead, with timeline"
    )
    market_position: str = Field(
        description="e.g. Challenger / Leader / Niche Player / Follower"
    )
    porter_strategy: str = Field(
        description="Differentiation Focus / Cost Leadership / Broad Differentiation"
    )
    confidence_score: int = Field(ge=0, le=100, default=76)
    key_competitor: str = Field(
        description="Named primary competitor and why they are the benchmark"
    )


# ── Financial Reasoning ────────────────────────────────────────────────────────
# Dissertation: McKinsey Three Horizons + NPV/IRR + Real Options

class InvestmentScenario(BaseModel):
    scenario: str = Field(description="e.g. Minimal Compliance (Horizon 1)")
    description: str
    capex: str = Field(description="e.g. $8m")
    opex_annual: str = Field(description="e.g. $3.2m")
    risk_reduction: str = Field(description="e.g. 28%")
    npv_3yr: str = Field(description="e.g. $12m")
    roi_3yr: str = Field(description="e.g. 42%")
    payback_months: int = Field(ge=0)


class FinancialReport(BaseModel):
    investment_scenarios: list[InvestmentScenario] = Field(
        min_length=2, max_length=3,
        description="2-3 investment scenarios (Horizon 1 / 2 / 3)"
    )
    cost_of_inaction: str = Field(
        description="Specific financial exposure: fines, revenue loss, attrition"
    )
    recommended_scenario: str
    recommended_budget: str
    revenue_protection: str = Field(
        description="Estimated $ revenue protected by proactive investment"
    )
    key_financial_drivers: list[str] = Field(
        min_length=2,
        description="Specific financial levers with quantified impact"
    )
    payback_period: str
    financial_risk_rating: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    sensitivity_factors: list[str] = Field(
        min_length=1,
        description="Factors that could improve or worsen ROI"
    )
    confidence_score: int = Field(ge=0, le=100, default=79)
    cfo_recommendation: str = Field(
        description="Single sentence investment recommendation with financial justification"
    )


# ── Synthesis ─────────────────────────────────────────────────────────────────
# Dissertation: Balanced Scorecard + McKinsey 7-S + Strategic Roadmapping

class RoadmapPhase(BaseModel):
    phase: str = Field(description="e.g. Phase 1: Foundation (0–12 months)")
    focus: str
    key_actions: list[str] = Field(min_length=1)
    investment: str = Field(description="e.g. $6m")
    success_metric: str = Field(description="Measurable KPI for phase completion")


class BalancedScorecard(BaseModel):
    financial: str = Field(description="Financial perspective: key metric and target")
    customer: str = Field(description="Customer/client trust perspective")
    internal_process: str = Field(description="Internal process perspective")
    learning_growth: str = Field(description="People and innovation perspective")


class SynthesisReport(BaseModel):
    executive_summary: str = Field(
        min_length=100,
        description="2-3 sentences: problem, findings, recommendation. Board-level precision."
    )
    strategic_imperatives: list[str] = Field(
        min_length=2,
        description="Specific, urgent, named actions with strategic rationale"
    )
    roadmap: list[RoadmapPhase] = Field(
        min_length=2, max_length=3,
        description="Phased strategic roadmap (0-12mo, 12-30mo, 30-60mo)"
    )
    balanced_scorecard: BalancedScorecard
    success_metrics: list[str] = Field(
        min_length=2,
        description="KPI: metric name, baseline, target, timeline"
    )
    decision_recommendation: Literal["PROCEED", "DEFER", "REJECT", "CONDITIONAL"]
    overall_confidence: int = Field(ge=0, le=100, default=82)
    board_narrative: str = Field(
        description="Single unforgettable sentence that frames the strategic imperative"
    )
    dissertation_contribution: str = Field(
        description="One sentence articulating how this multi-agent output advances AI-driven strategy theory"
    )


# Legacy alias — kept so _persist_results in analysis.py can store to DB unchanged
StrategicBrief = SynthesisReport

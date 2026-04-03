"""
Pydantic output schemas for every ASIS agent.
All agents validate their LLM output against these before passing downstream.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Agent 1 — Orchestrator ─────────────────────────────────────────────────


class SubTask(BaseModel):
    agent: str = Field(..., description="Agent name to execute this sub-task")
    objective: str = Field(..., description="Specific objective for the agent")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Agent names that must complete before this one",
    )
    priority: int = Field(ge=1, le=5, description="1=highest, 5=lowest")


class TaskPlan(BaseModel):
    query_type: str = Field(
        ..., description="Classified query type: market_entry, risk_only, financial, competitive, full"
    )
    subtasks: list[SubTask] = Field(..., description="Ordered list of subtasks")
    agent_sequence: list[str] = Field(
        ..., description="Ordered list of agent names to invoke"
    )
    parallel_agents: list[str] = Field(
        default_factory=list,
        description="Agents that can run in parallel",
    )
    reasoning: str = Field(..., description="Brief rationale for this execution plan")


# ── Agent 2 — Market Intelligence ─────────────────────────────────────────


class RegulationFlag(BaseModel):
    jurisdiction: str
    description: str
    impact: str = Field(..., description="low | medium | high")


class MarketIntelligenceReport(BaseModel):
    market_name: str
    market_size_usd_bn: Optional[float] = Field(
        None, description="Market size in USD billions"
    )
    growth_rate_pct: Optional[float] = Field(
        None, description="CAGR percentage"
    )
    forecast_year: Optional[int] = None
    key_trends: list[str] = Field(..., min_length=3)
    market_drivers: list[str] = Field(default_factory=list)
    market_barriers: list[str] = Field(default_factory=list)
    regulatory_flags: list[RegulationFlag] = Field(default_factory=list)
    target_segments: list[str] = Field(default_factory=list)
    geographic_focus: str = ""
    data_sources: list[str] = Field(..., min_length=1)
    analysis_limitations: list[str] = Field(default_factory=list)
    confidence: str = Field(..., description="low | medium | high")


# ── Agent 3 — Risk Assessment ──────────────────────────────────────────────


class RiskItem(BaseModel):
    risk_id: str = Field(..., description="Unique identifier e.g. GEO-001")
    risk_type: str = Field(
        ...,
        description="geopolitical | regulatory | operational | reputational | financial | cyber",
    )
    title: str
    description: str
    severity: int = Field(ge=1, le=10)
    likelihood: int = Field(ge=1, le=10)
    risk_score: float = Field(ge=1.0, le=100.0)
    time_horizon: str = Field(..., description="short (<1yr) | medium (1-3yr) | long (>3yr)")
    mitigation: list[str] = Field(..., min_length=2)
    data_sources: list[str] = Field(default_factory=list)


class RiskRegister(BaseModel):
    risk_items: list[RiskItem] = Field(..., min_length=1)
    overall_risk_level: str = Field(..., description="low | moderate | high | critical")
    top_risks: list[str] = Field(..., description="Risk IDs of top 3 risks", min_length=1)
    risk_summary: str
    data_sources: list[str] = Field(default_factory=list)


# ── Agent 4 — Financial Reasoning ─────────────────────────────────────────


class ComparableFirm(BaseModel):
    name: str
    ticker: Optional[str] = None
    revenue_usd_mn: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    notes: str = ""


class RevenueProjection(BaseModel):
    year: int
    low_usd_mn: float
    base_usd_mn: float
    high_usd_mn: float


class FinancialModel(BaseModel):
    capex_estimate_usd_mn: Optional[float] = Field(None, description="Initial capital expenditure")
    opex_annual_usd_mn: Optional[float] = Field(None, description="Annual operating costs")
    revenue_projections: list[RevenueProjection] = Field(default_factory=list)
    roi_estimate_pct: Optional[float] = None
    payback_period_years: Optional[float] = None
    npv_usd_mn: Optional[float] = None
    irr_pct: Optional[float] = None
    comparable_firms: list[ComparableFirm] = Field(default_factory=list)
    assumptions: list[str] = Field(..., min_length=3)
    sensitivity_factors: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="These projections are indicative estimates based on publicly available data. "
        "They do not constitute financial advice."
    )


# ── Agent 5 — Competitor Analysis ─────────────────────────────────────────


class FiveForce(BaseModel):
    force: str
    rating: str = Field(..., description="weak | moderate | strong | very_strong")
    score: int = Field(ge=1, le=10)
    rationale: str
    key_factors: list[str] = Field(default_factory=list)


class CompetitorProfile(BaseModel):
    name: str
    hq: str = ""
    founded: Optional[int] = None
    revenue_usd_mn: Optional[float] = None
    market_share_pct: Optional[float] = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    strategic_focus: str = ""
    recent_moves: list[str] = Field(default_factory=list)


class CompetitorBrief(BaseModel):
    five_forces: list[FiveForce] = Field(..., min_length=5, max_length=5)
    overall_competitive_intensity: str = Field(
        ..., description="low | moderate | high | very_high"
    )
    top_competitors: list[CompetitorProfile] = Field(..., min_length=1)
    positioning_map: dict[str, Any] = Field(
        default_factory=dict,
        description="Axis definitions and competitor coordinates",
    )
    strategic_white_space: list[str] = Field(
        ..., description="Identified market gaps and opportunities", min_length=1
    )
    sources: list[str] = Field(default_factory=list)


# ── Agent 6 — Synthesis ────────────────────────────────────────────────────


class StrategicOption(BaseModel):
    option_id: str
    title: str
    description: str
    rationale: str
    pros: list[str]
    cons: list[str]
    estimated_investment_usd_mn: Optional[float] = None
    time_to_value: str = ""
    risk_level: str = Field(..., description="low | medium | high")
    recommended: bool = False


class NextStep(BaseModel):
    priority: int = Field(ge=1, le=10)
    action: str
    owner: str = Field(..., description="Suggested responsible function/role")
    timeline: str
    success_criteria: str


class StrategicBrief(BaseModel):
    executive_summary: str = Field(..., min_length=100)
    recommendation: str = Field(
        ..., description="Lead recommendation in 2-3 sentences", min_length=50
    )
    strategic_options: list[StrategicOption] = Field(..., min_length=1)
    risk_summary: str
    financial_summary: str
    market_summary: str = ""
    competitive_summary: str = ""
    next_steps: list[NextStep] = Field(..., min_length=3)
    confidence_score: float = Field(ge=0.0, le=10.0)
    data_quality_score: float = Field(ge=0.0, le=10.0)
    caveats: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)

"""
ASIS v3.0 — Pydantic v2 agent output schemas.
Every agent validates its LLM output against these schemas (2 retries on fail).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Orchestrator ──────────────────────────────────────────────────────────────


class SubTask(BaseModel):
    agent: str = Field(description="Agent name responsible for this subtask")
    objective: str = Field(description="Clear objective for the agent")
    priority: int = Field(ge=1, le=5, description="1=critical, 5=low")
    context_keys: list[str] = Field(
        default_factory=list,
        description="AgentState keys this agent should read",
    )


class TaskPlan(BaseModel):
    query_type: Literal[
        "full_brief", "risk_only", "financial_only", "competitive", "custom"
    ]
    company_name: str
    sector: str
    geography: str
    agent_sequence: list[str] = Field(
        min_length=1, description="Ordered list of agents to execute"
    )
    subtasks: list[SubTask] = Field(min_length=1)
    memory_context: str = Field(
        default="", description="Relevant past analyses from Mem0"
    )
    memory_hit: bool = Field(
        default=False, description="True if Mem0 returned relevant context"
    )
    reasoning: str = Field(
        min_length=20, description="Orchestrator's routing rationale"
    )


# ── Market Intelligence ────────────────────────────────────────────────────────


class DataSource(BaseModel):
    name: str
    url: str = ""
    source_type: Literal["rag", "web", "api", "cache"] = "web"
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.8)


class MarketIntelligenceReport(BaseModel):
    market_name: str
    market_size_usd_bn: float = Field(ge=0)
    growth_rate_cagr_pct: float
    forecast_year: int = Field(ge=2024, le=2035)
    key_trends: list[str] = Field(
        min_length=3, description="Minimum 3 key market trends"
    )
    regulatory_flags: list[str] = Field(
        default_factory=list, description="Regulatory / compliance considerations"
    )
    entry_barriers: list[str] = Field(default_factory=list)
    rag_sources: list[DataSource] = Field(
        default_factory=list, description="Sources from Qdrant RAG retrieval"
    )
    web_sources: list[DataSource] = Field(
        default_factory=list, description="Sources from Tavily web search"
    )
    analyst_commentary: str = Field(
        min_length=100, description="Substantive analyst commentary"
    )


# ── Risk Assessment ────────────────────────────────────────────────────────────


class RiskItem(BaseModel):
    risk_id: str = Field(description="Short slug e.g. geopolitical_tension_india")
    category: Literal[
        "geopolitical", "regulatory", "operational", "financial", "reputational", "cyber"
    ]
    title: str
    description: str = Field(min_length=50)
    severity: int = Field(ge=1, le=10, description="Impact severity 1-10")
    likelihood: int = Field(ge=1, le=10, description="Probability 1-10")
    risk_score: float = Field(ge=1.0, le=100.0, description="severity × likelihood")
    mitigations: list[str] = Field(
        min_length=2, description="At least 2 mitigation strategies"
    )
    time_horizon: Literal["immediate", "short_term", "medium_term", "long_term"] = (
        "medium_term"
    )
    gdelt_sourced: bool = Field(
        default=False, description="True if sourced from GDELT cache"
    )

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v: float, info: object) -> float:
        # Allow slight deviation from strict product due to LLM rounding
        return round(max(1.0, min(100.0, v)), 2)


class RiskRegister(BaseModel):
    company_name: str
    assessment_scope: str
    risk_items: list[RiskItem] = Field(min_length=3)
    overall_risk_level: Literal["low", "moderate", "high", "critical"]
    executive_risk_summary: str = Field(min_length=100)
    top_risk_ids: list[str] = Field(
        min_length=1, max_length=3, description="IDs of top 3 risks"
    )


# ── Financial Reasoning ────────────────────────────────────────────────────────


class RevenueProjection(BaseModel):
    year: int
    low_usd_mn: float
    base_usd_mn: float
    high_usd_mn: float


class ComparableFirm(BaseModel):
    name: str
    ticker: str = ""
    revenue_usd_bn: float
    ebitda_margin_pct: float
    market_cap_usd_bn: float = 0.0
    data_source: str = "FMP"


class FinancialModel(BaseModel):
    company_name: str
    capex_estimate_usd_mn: float = Field(ge=0)
    opex_annual_usd_mn: float = Field(ge=0)
    revenue_projections: list[RevenueProjection] = Field(
        min_length=3, description="3-year revenue projections (low/base/high)"
    )
    roi_estimate_pct: float
    payback_period_years: float = Field(ge=0)
    npv_usd_mn: float
    irr_pct: float
    comparable_firms: list[ComparableFirm] = Field(
        default_factory=list, min_length=2
    )
    assumptions: list[str] = Field(
        min_length=3, description="Key modelling assumptions"
    )
    sensitivity_notes: str = Field(
        min_length=50, description="Key sensitivities and scenario flags"
    )
    crm_data_used: bool = Field(
        default=False, description="True if CRM company context informed the model"
    )


# ── Competitor Analysis ────────────────────────────────────────────────────────


class FiveForce(BaseModel):
    force: Literal[
        "supplier_power",
        "buyer_power",
        "competitive_rivalry",
        "threat_of_substitution",
        "threat_of_new_entry",
    ]
    score: int = Field(ge=1, le=10, description="Intensity 1=low, 10=high")
    rationale: str = Field(min_length=30)
    key_factors: list[str] = Field(min_length=1)


class CompetitorProfile(BaseModel):
    name: str
    hq_country: str = ""
    revenue_usd_bn: float = 0.0
    market_share_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    strategic_moves: list[str] = Field(default_factory=list)
    threat_level: Literal["low", "medium", "high", "critical"] = "medium"
    watchlist_sourced: bool = Field(
        default=False, description="True if from n8n competitor watchlist cache"
    )


class CompetitorBrief(BaseModel):
    company_name: str
    industry: str
    five_forces: list[FiveForce] = Field(
        min_length=5,
        max_length=5,
        description="Exactly 5 Porter forces required",
    )
    top_competitors: list[CompetitorProfile] = Field(min_length=2, max_length=8)
    strategic_white_space: list[str] = Field(
        min_length=1, description="Uncontested opportunity areas"
    )
    competitive_moat_assessment: str = Field(min_length=80)
    sources: list[str] = Field(default_factory=list)

    @field_validator("five_forces")
    @classmethod
    def exactly_five_forces(cls, v: list[FiveForce]) -> list[FiveForce]:
        force_names = {f.force for f in v}
        required = {
            "supplier_power",
            "buyer_power",
            "competitive_rivalry",
            "threat_of_substitution",
            "threat_of_new_entry",
        }
        missing = required - force_names
        if missing:
            raise ValueError(f"Missing Five Forces: {missing}")
        return v


# ── Synthesis ─────────────────────────────────────────────────────────────────


class StrategicOption(BaseModel):
    rank: int = Field(ge=1)
    title: str
    description: str = Field(min_length=50)
    pros: list[str] = Field(min_length=1)
    cons: list[str] = Field(min_length=1)
    estimated_investment_usd_mn: float = 0.0
    time_to_value_months: int = Field(ge=1)
    recommended: bool = False


class NextStep(BaseModel):
    priority: int = Field(ge=1, le=5)
    action: str
    owner_function: str = Field(
        description="Responsible business function e.g. Strategy, CFO, Legal"
    )
    timeline_weeks: int = Field(ge=1)
    dependencies: list[str] = Field(default_factory=list)


class StrategicBrief(BaseModel):
    company_name: str
    query_summary: str
    executive_summary: str = Field(
        min_length=200, description="Board-ready executive summary"
    )
    recommendation: str = Field(
        min_length=100,
        description="Primary recommended course of action",
    )
    strategic_options: list[StrategicOption] = Field(min_length=2)
    risk_summary: str = Field(min_length=80)
    financial_summary: str = Field(min_length=80)
    next_steps: list[NextStep] = Field(
        min_length=3, description="Minimum 3 actionable next steps"
    )
    confidence_score: float = Field(ge=0.0, le=10.0)
    data_quality_score: float = Field(ge=0.0, le=10.0)
    sources_count: int = Field(ge=0)
    caveats: list[str] = Field(default_factory=list)
    memory_delta: str = Field(
        default="",
        description="Delta vs prior ASIS recommendations (if Mem0 returned context)",
    )
    agents_used: list[str] = Field(default_factory=list)
    total_tokens: int = Field(ge=0, default=0)

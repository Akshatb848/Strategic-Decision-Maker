"""
Tests for all agent output Pydantic schemas.
Validates that schemas enforce constraints correctly.
"""

import pytest
from pydantic import ValidationError

from ..agents.schemas import (
    TaskPlan,
    SubTask,
    MarketIntelligenceReport,
    RegulationFlag,
    RiskRegister,
    RiskItem,
    FinancialModel,
    RevenueProjection,
    CompetitorBrief,
    FiveForce,
    CompetitorProfile,
    StrategicBrief,
    StrategicOption,
    NextStep,
)


# ── TaskPlan ──────────────────────────────────────────────────────────────────

class TestTaskPlan:
    def test_valid(self):
        plan = TaskPlan(
            query_type="full",
            subtasks=[
                SubTask(agent="market_intelligence", objective="Analyse market", dependencies=[], priority=1)
            ],
            agent_sequence=["market_intelligence", "synthesis"],
            parallel_agents=["market_intelligence"],
            reasoning="Standard full analysis",
        )
        assert plan.query_type == "full"

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            SubTask(agent="x", objective="y", dependencies=[], priority=6)

    def test_empty_agent_sequence_allowed(self):
        plan = TaskPlan(
            query_type="risk_only",
            subtasks=[],
            agent_sequence=[],
            reasoning="Risk only",
        )
        assert plan.agent_sequence == []


# ── MarketIntelligenceReport ──────────────────────────────────────────────────

class TestMarketIntelligenceReport:
    def test_valid_minimal(self):
        r = MarketIntelligenceReport(
            market_name="Indian Fintech",
            key_trends=["Digital payments", "Regulatory sandbox", "UPI growth"],
            data_sources=["World Bank 2024"],
            confidence="high",
        )
        assert r.market_name == "Indian Fintech"
        assert r.growth_rate_pct is None

    def test_requires_3_trends(self):
        with pytest.raises(ValidationError):
            MarketIntelligenceReport(
                market_name="Test",
                key_trends=["Only one trend"],
                data_sources=["Source"],
                confidence="low",
            )

    def test_requires_data_sources(self):
        with pytest.raises(ValidationError):
            MarketIntelligenceReport(
                market_name="Test",
                key_trends=["t1", "t2", "t3"],
                data_sources=[],
                confidence="medium",
            )

    def test_regulation_flag(self):
        flag = RegulationFlag(
            jurisdiction="India",
            description="RBI digital lending guidelines",
            impact="high",
        )
        assert flag.impact == "high"


# ── RiskRegister ──────────────────────────────────────────────────────────────

class TestRiskRegister:
    def _risk_item(self, **kwargs):
        defaults = dict(
            risk_id="GEO-001",
            risk_type="geopolitical",
            title="Political instability",
            description="Risk of government policy reversal",
            severity=7,
            likelihood=4,
            risk_score=28.0,
            time_horizon="medium (1-3yr)",
            mitigation=["Scenario planning", "Political risk insurance"],
        )
        defaults.update(kwargs)
        return RiskItem(**defaults)

    def test_valid_risk(self):
        item = self._risk_item()
        assert item.severity == 7
        assert item.risk_score == 28.0

    def test_severity_bounds(self):
        with pytest.raises(ValidationError):
            self._risk_item(severity=11)

    def test_likelihood_bounds(self):
        with pytest.raises(ValidationError):
            self._risk_item(likelihood=0)

    def test_requires_two_mitigations(self):
        with pytest.raises(ValidationError):
            self._risk_item(mitigation=["Only one"])

    def test_valid_register(self):
        reg = RiskRegister(
            risk_items=[self._risk_item()],
            overall_risk_level="moderate",
            top_risks=["GEO-001"],
            risk_summary="Moderate risk profile",
        )
        assert reg.overall_risk_level == "moderate"


# ── FinancialModel ────────────────────────────────────────────────────────────

class TestFinancialModel:
    def test_valid(self):
        m = FinancialModel(
            assumptions=["Market penetration 1%", "ARPU $50", "3yr horizon"],
        )
        assert len(m.assumptions) == 3

    def test_requires_three_assumptions(self):
        with pytest.raises(ValidationError):
            FinancialModel(assumptions=["Only one", "Only two"])

    def test_revenue_projection(self):
        proj = RevenueProjection(year=2026, low_usd_mn=10.0, base_usd_mn=20.0, high_usd_mn=35.0)
        assert proj.base_usd_mn == 20.0


# ── CompetitorBrief ───────────────────────────────────────────────────────────

class TestCompetitorBrief:
    def _force(self, name: str):
        return FiveForce(
            force=name,
            rating="strong",
            score=7,
            rationale="High barriers",
        )

    def test_requires_five_forces(self):
        forces = [self._force(f"Force {i}") for i in range(4)]
        with pytest.raises(ValidationError):
            CompetitorBrief(
                five_forces=forces,
                overall_competitive_intensity="high",
                top_competitors=[],
                strategic_white_space=["Gap 1"],
            )

    def test_valid_brief(self):
        forces = [self._force(f"Force {i}") for i in range(5)]
        brief = CompetitorBrief(
            five_forces=forces,
            overall_competitive_intensity="high",
            top_competitors=[
                CompetitorProfile(name="Competitor A")
            ],
            strategic_white_space=["SME segment underserved"],
        )
        assert len(brief.five_forces) == 5


# ── StrategicBrief ────────────────────────────────────────────────────────────

class TestStrategicBrief:
    def test_valid(self):
        brief = StrategicBrief(
            executive_summary="A" * 100,
            recommendation="B" * 50,
            strategic_options=[
                StrategicOption(
                    option_id="OPT-001",
                    title="Market Entry",
                    description="Enter via JV",
                    rationale="Lower risk",
                    pros=["Speed to market"],
                    cons=["Profit sharing"],
                    risk_level="medium",
                )
            ],
            risk_summary="Moderate risk profile",
            financial_summary="Positive NPV expected",
            next_steps=[
                NextStep(priority=1, action="Sign MOU", owner="CEO", timeline="Q3 2026", success_criteria="MOU signed"),
                NextStep(priority=2, action="Hire country manager", owner="CHRO", timeline="Q4 2026", success_criteria="Hired"),
                NextStep(priority=3, action="Regulatory filing", owner="Legal", timeline="Q1 2027", success_criteria="Filed"),
            ],
            confidence_score=7.5,
            data_quality_score=7.0,
        )
        assert brief.confidence_score == 7.5

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            StrategicBrief(
                executive_summary="A" * 100,
                recommendation="B" * 50,
                strategic_options=[],
                risk_summary="x",
                financial_summary="x",
                next_steps=[
                    NextStep(priority=1, action="a", owner="b", timeline="c", success_criteria="d"),
                    NextStep(priority=2, action="e", owner="f", timeline="g", success_criteria="h"),
                    NextStep(priority=3, action="i", owner="j", timeline="k", success_criteria="l"),
                ],
                confidence_score=11.0,
                data_quality_score=5.0,
            )

"""
ASIS LangGraph StateGraph definition.

Pipeline:
  START → orchestrator → [market_intelligence, risk_assessment, competitor_analysis] (parallel)
        → financial_reasoning → synthesis → END

Conditional edges from orchestrator allow skipping agents not required
for the query type (e.g., risk-only query skips financial_reasoning).
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.constants import Send

from .state import AgentState
from ..agents.orchestrator import OrchestratorAgent
from ..agents.market_intelligence import MarketIntelligenceAgent
from ..agents.risk_assessment import RiskAssessmentAgent
from ..agents.financial_reasoning import FinancialReasoningAgent
from ..agents.competitor_analysis import CompetitorAnalysisAgent
from ..agents.synthesis import SynthesisAgent

# ── Instantiate agents (singletons for the graph lifetime) ─────────────────
_orchestrator = OrchestratorAgent()
_market = MarketIntelligenceAgent()
_risk = RiskAssessmentAgent()
_financial = FinancialReasoningAgent()
_competitor = CompetitorAnalysisAgent()
_synthesis = SynthesisAgent()


# ── Node wrappers ──────────────────────────────────────────────────────────

async def orchestrator_node(state: AgentState) -> AgentState:
    return await _orchestrator.execute(state)


async def market_intelligence_node(state: AgentState) -> AgentState:
    return await _market.execute(state)


async def risk_assessment_node(state: AgentState) -> AgentState:
    return await _risk.execute(state)


async def financial_reasoning_node(state: AgentState) -> AgentState:
    return await _financial.execute(state)


async def competitor_analysis_node(state: AgentState) -> AgentState:
    return await _competitor.execute(state)


async def synthesis_node(state: AgentState) -> AgentState:
    return await _synthesis.execute(state)


# ── Routing functions ──────────────────────────────────────────────────────

PARALLEL_AGENTS = {"market_intelligence", "risk_assessment", "competitor_analysis"}

QueryType = Literal["full", "market_entry", "risk_only", "financial", "competitive"]

_QUERY_TYPE_TO_PARALLEL: dict[str, list[str]] = {
    "full": ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "market_entry": ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "risk_only": ["risk_assessment"],
    "financial": ["market_intelligence"],
    "competitive": ["competitor_analysis", "market_intelligence"],
}

_QUERY_TYPE_NEEDS_FINANCIAL: set[str] = {"full", "market_entry", "financial"}


def route_after_orchestrator(state: AgentState) -> list[str] | str:
    """
    After orchestrator: determine which parallel agents to spawn,
    or go directly to synthesis if it's a simple query.
    Uses Send() for parallel fanout.
    """
    task_plan = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full")
    parallel = _QUERY_TYPE_TO_PARALLEL.get(query_type, ["market_intelligence", "risk_assessment"])

    if not parallel:
        return "synthesis"

    # Return list of node names for parallel execution
    return parallel


def route_after_parallel(state: AgentState) -> str:
    """
    After parallel agents complete: decide whether financial_reasoning is needed.
    """
    task_plan = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full")
    agent_sequence: list[str] = state.get("agent_sequence") or []

    if "financial_reasoning" in agent_sequence or query_type in _QUERY_TYPE_NEEDS_FINANCIAL:
        return "financial_reasoning"
    return "synthesis"


# ── Graph construction ─────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and compile the ASIS StateGraph. Returns the compiled graph."""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("market_intelligence", market_intelligence_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("financial_reasoning", financial_reasoning_node)
    builder.add_node("competitor_analysis", competitor_analysis_node)
    builder.add_node("synthesis", synthesis_node)

    # Start → orchestrator
    builder.add_edge(START, "orchestrator")

    # Orchestrator → parallel agents (conditional fanout)
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "market_intelligence": "market_intelligence",
            "risk_assessment": "risk_assessment",
            "competitor_analysis": "competitor_analysis",
            "synthesis": "synthesis",
        },
    )

    # Each parallel agent → route to financial or synthesis
    for parallel_agent in ["market_intelligence", "risk_assessment", "competitor_analysis"]:
        builder.add_conditional_edges(
            parallel_agent,
            route_after_parallel,
            {
                "financial_reasoning": "financial_reasoning",
                "synthesis": "synthesis",
            },
        )

    # Financial → synthesis
    builder.add_edge("financial_reasoning", "synthesis")

    # Synthesis → END
    builder.add_edge("synthesis", END)

    return builder.compile()


# Module-level compiled graph instance
asis_graph = build_graph()

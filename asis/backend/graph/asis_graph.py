"""
ASIS v4.0 — LangGraph 1.0 StateGraph.

Pipeline topology (fixed fan-in)
---------------------------------
START → orchestrator → parallel fanout (list return, NOT Send) →
    parallel: subset of [market_intelligence, risk_assessment, competitor_analysis]
    (subset chosen by query_type) →
    gather  ← explicit fan-in node; all parallel agents route here ←
    → financial_reasoning (sequential, when needed) →
    synthesis → END

WHY list-return instead of Send():
  Send() creates independent channels — each parallel agent independently routes
  financial_reasoning and synthesis, so synthesis ran 3× with only 1 specialist
  report each time instead of all 4 combined.

  Returning a list of strings from the routing function (LangGraph 1.0 supported)
  runs those nodes in the same superstep with proper fan-in: their states are
  merged via reducers in state.py before the next node starts.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END

from asis.backend.graph.state import AgentState
from asis.backend.agents.orchestrator import OrchestratorAgent
from asis.backend.agents.market_intelligence import MarketIntelligenceAgent
from asis.backend.agents.risk_assessment import RiskAssessmentAgent
from asis.backend.agents.financial_reasoning import FinancialReasoningAgent
from asis.backend.agents.competitor_analysis import CompetitorAnalysisAgent
from asis.backend.agents.synthesis import SynthesisAgent
from asis.backend.config.logging import get_logger

logger = get_logger(__name__)

# ── Singleton agent instances ──────────────────────────────────────────────────

_orchestrator = OrchestratorAgent()
_market = MarketIntelligenceAgent()
_risk = RiskAssessmentAgent()
_financial = FinancialReasoningAgent()
_competitor = CompetitorAnalysisAgent()
_synthesis = SynthesisAgent()

# ── Routing configuration ──────────────────────────────────────────────────────

# Maps query_type → list of parallel agent node names.
# financial_reasoning is intentionally NEVER in the parallel batch — it runs
# sequentially after gather so it always receives all specialist outputs.
_QUERY_TYPE_PARALLEL: dict[str, list[str]] = {
    "risk_only":      ["risk_assessment"],
    "financial_only": ["market_intelligence"],
    "competitive":    ["market_intelligence", "competitor_analysis"],
    "full_brief":     ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "custom":         ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "full":           ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "market_entry":   ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "financial":      ["market_intelligence"],
}

# Query types that require financial_reasoning after the parallel gather phase.
_NEEDS_FINANCIAL: frozenset[str] = frozenset({
    "full_brief", "custom", "full", "market_entry",
    "financial_only", "financial",
})

# All possible parallel node names (used for graph edge registration)
_ALL_PARALLEL_NODES: list[str] = [
    "market_intelligence",
    "risk_assessment",
    "competitor_analysis",
]


# ── Node functions ─────────────────────────────────────────────────────────────

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


async def gather_node(state: AgentState) -> dict:
    """
    Explicit fan-in point — all parallel agents route here via regular edges.

    LangGraph invokes gather ONCE after ALL parallel agents in the current
    superstep complete, with their outputs already merged via state reducers.
    Returns an empty dict (no state changes) — the merged state from parallel
    agents passes through unchanged.
    """
    logger.info(
        "gather_node",
        has_market=bool(state.get("market_report")),
        has_risk=bool(state.get("risk_register")),
        has_competitor=bool(state.get("competitor_brief")),
        has_financial=bool(state.get("financial_model")),
        analysis_id=state.get("analysis_id"),
    )
    return {}


# ── Conditional edge functions ─────────────────────────────────────────────────

def route_from_orchestrator(state: AgentState) -> list[str]:
    """
    Fan-out from orchestrator. Returns a LIST of node names to execute in parallel.

    Returning a list (not Send objects) means LangGraph runs the listed nodes
    in the SAME superstep with proper fan-in at the gather node.
    All parallel nodes start with the same state snapshot and their outputs
    are merged via reducers before gather runs.
    """
    task_plan: dict[str, Any] = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full_brief")

    parallel_nodes = _QUERY_TYPE_PARALLEL.get(
        query_type,
        ["market_intelligence", "risk_assessment", "competitor_analysis"],
    )

    logger.info(
        "graph_route_orchestrator",
        query_type=query_type,
        parallel_nodes=parallel_nodes,
        analysis_id=state.get("analysis_id"),
    )

    return parallel_nodes


def route_from_gather(state: AgentState) -> str:
    """
    After gather (fan-in complete, all specialist outputs merged), decide:
      - financial_reasoning if the query type needs financial modelling
      - synthesis directly if financial_reasoning is not needed
    """
    task_plan: dict[str, Any] = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full_brief")

    if query_type in _NEEDS_FINANCIAL:
        logger.info(
            "gather_route_financial",
            query_type=query_type,
            analysis_id=state.get("analysis_id"),
        )
        return "financial_reasoning"

    logger.info(
        "gather_route_synthesis",
        query_type=query_type,
        analysis_id=state.get("analysis_id"),
    )
    return "synthesis"


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Build and compile the ASIS StateGraph.

    Parameters
    ----------
    checkpointer : optional
        A LangGraph checkpointer instance. If None, runs without persistence.
    """
    builder = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("market_intelligence", market_intelligence_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("financial_reasoning", financial_reasoning_node)
    builder.add_node("competitor_analysis", competitor_analysis_node)
    builder.add_node("gather", gather_node)
    builder.add_node("synthesis", synthesis_node)

    # ── START → orchestrator ───────────────────────────────────────────────────
    builder.add_edge(START, "orchestrator")

    # ── orchestrator → parallel fanout (list return = proper fan-in) ──────────
    builder.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        # path_map: all possible parallel target node names
        _ALL_PARALLEL_NODES,
    )

    # ── parallel agents → gather (regular edges; LangGraph fans them in) ──────
    # gather waits for ALL nodes that were started in the parallel superstep.
    # Nodes not started for a given query_type don't block gather.
    for parallel_node in _ALL_PARALLEL_NODES:
        builder.add_edge(parallel_node, "gather")

    # ── gather → financial_reasoning or synthesis (once, with merged state) ───
    builder.add_conditional_edges(
        "gather",
        route_from_gather,
        {
            "financial_reasoning": "financial_reasoning",
            "synthesis": "synthesis",
        },
    )

    # ── financial_reasoning → synthesis ───────────────────────────────────────
    builder.add_edge("financial_reasoning", "synthesis")

    # ── synthesis → END ───────────────────────────────────────────────────────
    builder.add_edge("synthesis", END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return builder.compile(**compile_kwargs)


async def get_graph_with_checkpointer(db_url: str):
    """
    Build and return a compiled graph backed by AsyncPostgresSaver.
    Falls back to MemorySaver if postgres is unavailable.
    """
    psycopg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = AsyncPostgresSaver.from_conn_string(psycopg_url)
        await checkpointer.setup()
        logger.info("graph_checkpointer_ready", backend="postgres")
        return build_graph(checkpointer=checkpointer)
    except Exception as exc:
        logger.warning(
            "graph_checkpointer_fallback",
            error=str(exc),
            backend="memory",
        )
        from langgraph.checkpoint.memory import MemorySaver

        return build_graph(checkpointer=MemorySaver())


# ── Module-level default graph (no checkpointer) ──────────────────────────────
asis_graph = build_graph()

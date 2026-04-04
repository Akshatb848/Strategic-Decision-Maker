"""
SingleAgentBaseline v3.0 — processes the same query with a single LLM call,
no agent decomposition. Used for dissertation comparison against the
multi-agent ASIS pipeline (Wilcoxon signed-rank test).

Model: claude_haiku_model (haiku) for cost efficiency on dissertation runs.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import get_logger, get_settings
from ..db import BaselineRun
from .engine import EvaluationEngine

settings = get_settings()
logger = get_logger(__name__)

_BASELINE_SYSTEM_PROMPT = """\
You are a senior strategy consultant advising a multinational corporation.
You will receive a strategic question and company context.
Your task is to produce a comprehensive strategic brief in a single response.

The brief must include:
1. Executive summary (200-400 words)
2. Primary recommendation (2-3 sentences)
3. Market analysis (market size, trends, regulatory environment)
4. Risk assessment (at least 5 risks scored on severity and likelihood)
5. Financial considerations (cost estimates, revenue projections where possible)
6. Competitive analysis (key competitors and market positioning)
7. Strategic options (2-4 ranked options with pros/cons)
8. Next steps (at least 5 specific, actionable, time-bound steps)
9. Confidence score (0-10)
10. Data quality score (0-10)

Cite sources for every claim. State assumptions explicitly. Do not fabricate data.

Output valid JSON matching this structure:
{
  "executive_summary": "string",
  "recommendation": "string",
  "market_analysis": "string",
  "risk_assessment": "string",
  "financial_considerations": "string",
  "competitive_analysis": "string",
  "strategic_options": [{"title": "string", "description": "string", "pros": [], "cons": []}],
  "next_steps": [{"priority": 1, "action": "string", "timeline": "string"}],
  "confidence_score": 0.0,
  "data_quality_score": 0.0,
  "sources": []
}
"""


class SingleAgentBaseline:
    """
    Runs the full strategic query through a single LiteLLM call (Haiku model).

    Does NOT use the multi-agent pipeline — this is the dissertation control condition.
    Results are scored by EvaluationEngine and stored as a BaselineRun ORM object.
    """

    def __init__(self) -> None:
        import litellm  # type: ignore[import]
        self._litellm = litellm
        self._model = settings.claude_haiku_model
        self._eval_engine = EvaluationEngine()

    async def run(
        self,
        query: str,
        company_context: dict[str, Any],
        tenant_id: str,
    ) -> BaselineRun:
        """
        Execute single-agent baseline and return a populated BaselineRun ORM object.

        The returned object is NOT committed to the database — the caller must
        add it to a session and commit.
        """
        start_ms = int(time.time() * 1000)

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(company_context, indent=2)}\n\n"
            "Produce the full strategic brief JSON now."
        )

        output: dict[str, Any] = {}
        tokens_used = 0

        try:
            response = await self._litellm.acompletion(
                model=self._model,
                messages=[
                    {"role": "system", "content": _BASELINE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=settings.claude_max_tokens,
                temperature=0.3,
                api_base=settings.litellm_proxy_url,
                api_key=settings.litellm_master_key.get_secret_value(),
            )

            raw_text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```(?:json)?\s*", "", clean)
                clean = re.sub(r"\s*```$", "", clean).strip()
            output = json.loads(clean)

        except json.JSONDecodeError as exc:
            logger.error("baseline_json_parse_failed", error=str(exc))
            output = {
                "executive_summary": "Baseline run failed: JSON parse error",
                "recommendation": "",
                "sources": [],
                "confidence_score": 0.0,
                "data_quality_score": 0.0,
            }
        except Exception as exc:
            logger.error("baseline_run_failed", model=self._model, error=str(exc))
            output = {
                "executive_summary": f"Baseline run failed: {exc}",
                "recommendation": "",
                "sources": [],
                "confidence_score": 0.0,
                "data_quality_score": 0.0,
            }

        duration_ms = int(time.time() * 1000) - start_ms

        logger.info(
            "baseline_run_complete",
            model=self._model,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )

        scores: dict[str, float] = {}
        try:
            scores = await self._eval_engine.evaluate(output, query)
        except Exception as exc:
            logger.warning("baseline_eval_failed", error=str(exc))
            scores = {
                "analytical_depth": 5.0,
                "factual_accuracy": 5.0,
                "contextual_relevance": 5.0,
                "actionability": 5.0,
                "internal_consistency": 5.0,
                "overall_score": 5.0,
            }

        return BaselineRun(
            output=output,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            eval_analytical_depth=scores.get("analytical_depth"),
            eval_factual_accuracy=scores.get("factual_accuracy"),
            eval_contextual_relevance=scores.get("contextual_relevance"),
            eval_actionability=scores.get("actionability"),
            eval_internal_consistency=scores.get("internal_consistency"),
            eval_overall_score=scores.get("overall_score"),
        )

"""
SingleAgentBaseline — processes the same query with a single Claude call,
no agent decomposition. Used for dissertation comparison against the
multi-agent ASIS pipeline.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic

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
9. Confidence and data quality scores (0-10 each)

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
    """Runs the full strategic query through a single Claude call for comparison."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self._eval_engine = EvaluationEngine()

    async def run(
        self,
        query: str,
        company_context: dict[str, Any],
        analysis_id: uuid.UUID,
    ) -> BaselineRun:
        """
        Execute single-agent baseline and return a populated BaselineRun ORM object
        (not yet committed — caller must add to session and commit).
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
            full_text = ""
            async with self._client.messages.stream(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                thinking={"type": "adaptive"},
                system=_BASELINE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                async for text in stream.text_stream:
                    full_text += text
                final = await stream.get_final_message()
                tokens_used = (
                    final.usage.input_tokens + final.usage.output_tokens
                    if final.usage else 0
                )

            # Parse output
            clean = full_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```", 2)[1]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.rsplit("```", 1)[0].strip()
            output = json.loads(clean)

        except Exception as exc:
            logger.error("baseline_run_failed", error=str(exc))
            output = {"error": str(exc), "executive_summary": "Baseline run failed"}

        duration_ms = int(time.time() * 1000) - start_ms

        # Evaluate
        scores: dict[str, float] = {}
        try:
            scores = await self._eval_engine.evaluate(output, query)
        except Exception as exc:
            logger.warning("baseline_eval_failed", error=str(exc))

        return BaselineRun(
            analysis_id=analysis_id,
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

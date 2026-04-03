"""
EvaluationEngine — scores StrategicBrief outputs on five dimensions.
Used for the dissertation's quantitative comparison of multi-agent vs single-agent.

Dimensions (each 0-10):
  analytical_depth     — breadth of factors considered
  factual_accuracy     — sources cited vs. claims made ratio
  contextual_relevance — alignment of output to query specifics
  actionability        — quality and specificity of next_steps
  internal_consistency — coherence across agent outputs
  overall_score        — weighted average using config/settings.py weights
"""

from __future__ import annotations

import json
import re
from typing import Any

import anthropic

from ..config import get_logger, get_settings

settings = get_settings()
logger = get_logger(__name__)

_EVAL_SYSTEM_PROMPT = """\
You are an expert evaluator of strategic consulting reports. You will score a strategic brief
on five dimensions, each on a scale from 0 to 10 (where 10 is exceptional quality).

Scoring definitions:
- analytical_depth (0-10): How thoroughly are relevant strategic factors considered?
  10 = all major strategic dimensions covered with evidence; 0 = superficial or missing analysis
- factual_accuracy (0-10): Are claims backed by cited sources?
  10 = every claim has a traceable source; 0 = no sources cited, claims appear fabricated
- contextual_relevance (0-10): How well does the output address the specific query?
  10 = perfectly tailored to the exact strategic question; 0 = generic, could apply to any company
- actionability (0-10): How specific and implementable are the next steps and recommendations?
  10 = specific, time-bound, owner-assigned actions; 0 = vague platitudes
- internal_consistency (0-10): Are all sections coherent and free of contradictions?
  10 = all sections tell a unified story; 0 = contradictions between sections

Output valid JSON ONLY:
{
  "analytical_depth": float,
  "factual_accuracy": float,
  "contextual_relevance": float,
  "actionability": float,
  "internal_consistency": float,
  "reasoning": "brief explanation of scores (2-3 sentences)"
}
"""


class EvaluationEngine:
    """Scores strategic brief outputs using Claude as the evaluator."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    async def evaluate(
        self,
        strategic_brief: dict[str, Any],
        original_query: str,
    ) -> dict[str, float]:
        """
        Score a StrategicBrief on all five dimensions.
        Returns a dict with all five dimension scores + overall_score.
        """
        prompt = (
            f"Original Query: {original_query}\n\n"
            f"Strategic Brief to Evaluate:\n{json.dumps(strategic_brief, indent=2)}\n\n"
            "Score this brief on all five dimensions. Output valid JSON only."
        )

        try:
            response = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=1000,
                thinking={"type": "adaptive"},
                system=_EVAL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            text = next(
                (b.text for b in response.content if b.type == "text"), "{}"
            )
            clean = _strip_fences(text)
            scores_raw = json.loads(clean)

        except Exception as exc:
            logger.warning("evaluation_failed", error=str(exc))
            # Return neutral scores on failure rather than crashing
            scores_raw = {
                "analytical_depth": 5.0,
                "factual_accuracy": 5.0,
                "contextual_relevance": 5.0,
                "actionability": 5.0,
                "internal_consistency": 5.0,
            }

        # Clamp all scores to [0, 10]
        scores: dict[str, float] = {}
        for dim in [
            "analytical_depth",
            "factual_accuracy",
            "contextual_relevance",
            "actionability",
            "internal_consistency",
        ]:
            raw = float(scores_raw.get(dim, 5.0))
            scores[dim] = max(0.0, min(10.0, raw))

        # Compute weighted overall score
        weights = settings.eval_weights
        overall = sum(scores[dim] * weights[dim] for dim in weights)
        scores["overall_score"] = round(overall, 2)

        return scores


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

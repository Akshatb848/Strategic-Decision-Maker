"""
EvaluationEngine v3.0 — scores StrategicBrief outputs on five dimensions.

Used for the dissertation's quantitative comparison of multi-agent vs single-agent.

Dimensions (each 0-10):
  analytical_depth     — breadth of factors considered
  factual_accuracy     — sources cited vs claims made ratio
  contextual_relevance — alignment of output to query specifics
  actionability        — quality and specificity of next_steps
  internal_consistency — coherence across agent outputs
  overall_score        — weighted average using settings.eval_weights

Model: claude_haiku_model (cheap, fast) for cost-efficient dissertation runs.
Returns neutral 5.0 scores on any failure rather than crashing.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import get_logger, get_settings
from ..schemas.evaluation import DimensionScore, EvaluationResult

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

_NEUTRAL_SCORES: dict[str, float] = {
    "analytical_depth": 5.0,
    "factual_accuracy": 5.0,
    "contextual_relevance": 5.0,
    "actionability": 5.0,
    "internal_consistency": 5.0,
}

_DIMENSIONS = list(_NEUTRAL_SCORES.keys())


class EvaluationEngine:
    """
    Scores strategic brief outputs using LiteLLM (Haiku model for cost efficiency).

    All evaluation calls route through the LiteLLM proxy — never directly to Anthropic.
    Returns neutral 5.0 scores on any failure rather than propagating exceptions.
    """

    def __init__(self) -> None:
        import litellm  # type: ignore[import]

        self._litellm = litellm
        self._model = settings.claude_haiku_model

    async def evaluate(
        self,
        strategic_brief_dict: dict[str, Any],
        query: str,
        baseline_output: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Score a StrategicBrief on all five evaluation dimensions.

        Args:
            strategic_brief_dict: The StrategicBrief JSON dict to evaluate.
            query: The original strategic query (provides context for relevance scoring).
            baseline_output: Optional baseline dict — not scored here, used for reference only.

        Returns:
            dict with keys: analytical_depth, factual_accuracy, contextual_relevance,
            actionability, internal_consistency, overall_score (all floats 0-10).
        """
        prompt = (
            f"Original Query: {query}\n\n"
            f"Strategic Brief to Evaluate:\n{json.dumps(strategic_brief_dict, indent=2)}\n\n"
            "Score this brief on all five dimensions. Output valid JSON only."
        )

        scores_raw: dict[str, Any] = {}
        try:
            response = await self._litellm.acompletion(
                model=self._model,
                messages=[
                    {"role": "system", "content": _EVAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.0,  # deterministic scoring
                api_base=settings.litellm_proxy_url,
                api_key=settings.litellm_master_key.get_secret_value(),
            )
            raw_text = response.choices[0].message.content or "{}"
            clean = _strip_fences(raw_text)
            scores_raw = json.loads(clean)

        except Exception as exc:
            logger.warning(
                "evaluation_failed",
                model=self._model,
                error=str(exc),
                note="returning_neutral_scores",
            )
            return {**_NEUTRAL_SCORES, "overall_score": 5.0}

        # Clamp all dimension scores to [0, 10]
        scores: dict[str, float] = {}
        for dim in _DIMENSIONS:
            raw = float(scores_raw.get(dim, 5.0))
            scores[dim] = max(0.0, min(10.0, raw))

        # Compute weighted overall score using config weights
        weights = settings.eval_weights
        overall = sum(scores[dim] * weights.get(dim, 0.2) for dim in _DIMENSIONS)
        scores["overall_score"] = round(overall, 2)

        logger.info(
            "evaluation_complete",
            model=self._model,
            overall_score=scores["overall_score"],
        )
        return scores

    def build_evaluation_result(
        self,
        scores: dict[str, float],
        analysis_id: str,
        report_type: str,
        evaluation_tokens: int = 0,
    ) -> EvaluationResult:
        """
        Wrap a raw scores dict into the structured EvaluationResult schema.

        Useful when callers need the full DimensionScore objects with rationale.
        """
        weights = settings.eval_weights

        def _dim(name: str) -> DimensionScore:
            score = scores.get(name, 5.0)
            weight = weights.get(name, 0.2)
            return DimensionScore(
                score=score,
                weight=weight,
                rationale="Computed by EvaluationEngine",
                weighted_contribution=round(score * weight, 4),
            )

        return EvaluationResult(
            analysis_id=analysis_id,
            report_type=report_type,
            analytical_depth=_dim("analytical_depth"),
            factual_accuracy=_dim("factual_accuracy"),
            contextual_relevance=_dim("contextual_relevance"),
            actionability=_dim("actionability"),
            internal_consistency=_dim("internal_consistency"),
            overall_score=scores.get("overall_score", 5.0),
            evaluator_model=self._model,
            evaluation_tokens=evaluation_tokens,
            evaluated_at=datetime.now(tz=timezone.utc).isoformat(),
        )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

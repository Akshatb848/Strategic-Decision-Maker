"""
ASIS v3.0 — BaseAgent ABC.
All LLM calls go directly to the Anthropic Messages API via httpx.
Every run wrapped in a Langfuse trace span (optional).
"""
from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, TypeVar

import httpx
from pydantic import BaseModel

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.graph.state import AgentState

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)
_SSECallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]

# Global semaphore — LiteLLM proxy handles per-provider rate limiting.
# Allow up to 6 concurrent in-flight calls (one per agent + headroom).
_LLM_SEMAPHORE = asyncio.Semaphore(6)


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._langfuse = self._init_langfuse()

    def _init_langfuse(self) -> Any:
        if not self._settings.langfuse_enabled:
            return None
        try:
            from langfuse import Langfuse
            return Langfuse(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key.get_secret_value(),
                host=self._settings.langfuse_host,
            )
        except Exception:
            return None

    def _start_span(self, trace_id: str, metadata: dict[str, Any] | None = None) -> Any:
        if not self._langfuse:
            return None
        try:
            trace = self._langfuse.trace(id=trace_id, name=f"asis.{self.name}")
            return trace.span(name=self.name, metadata=metadata or {})
        except Exception:
            return None

    def _end_span(self, span: Any, tokens: int = 0, error: str | None = None) -> None:
        if not span:
            return
        try:
            if error:
                span.update(level="ERROR", status_message=error)
            else:
                span.update(usage={"total_tokens": tokens})
            span.end()
            if self._langfuse:
                self._langfuse.flush()
        except Exception:
            pass

    # ── SSE log emission ───────────────────────────────────────────────────────

    async def _emit(self, state: AgentState, event: str, data: dict[str, Any]) -> None:
        cb: _SSECallback | None = state.get("metadata", {}).get("sse_callback")
        if cb:
            try:
                await cb(event, data)
            except Exception:
                pass

    async def _log(self, state: AgentState, level: str, message: str) -> None:
        """Emit a structured agent_log SSE event (shows in Pipeline Log panel)."""
        await self._emit(state, "agent_log", {
            "agent": self.name,
            "level": level,
            "message": message,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

    # ── Core execution ─────────────────────────────────────────────────────────

    async def execute(self, state: AgentState) -> AgentState:
        start_ms = int(time.time() * 1000)
        analysis_id = state.get("analysis_id", "unknown")
        trace_id = str(state.get("metadata", {}).get("trace_id", analysis_id))
        span = self._start_span(trace_id, {"agent": self.name})

        await self._emit(state, "agent_start", {"agent": self.name, "analysis_id": analysis_id})
        await self._log(state, "info", f"[{self.name.upper()}] Starting analysis...")
        logger.info("agent_start", agent=self.name, analysis_id=analysis_id)

        try:
            updated = await self.run(state)
            duration = int(time.time() * 1000) - start_ms

            # ── Per-agent token tracking ──────────────────────────────────────
            tokens = int(updated.get("metadata", {}).get(f"_tokens_{self.name}", 0))
            total_tokens = int(updated.get("metadata", {}).get("total_tokens", 0))

            await self._emit(updated, "agent_complete", {
                "agent": self.name,
                "duration_ms": duration,
                "tokens": tokens,
            })
            await self._log(updated, "success",
                f"[{self.name.upper()}] Complete — {tokens}t · {duration}ms")
            logger.info("agent_complete", agent=self.name, duration_ms=duration, tokens=tokens)
            self._end_span(span, tokens=tokens)
            return updated

        except Exception as exc:
            duration = int(time.time() * 1000) - start_ms
            exc_str = str(exc)
            # Provide actionable guidance for the most common failure modes
            if "401" in exc_str or "Unauthorized" in exc_str or "authentication" in exc_str.lower():
                human_msg = f"[{self.name.upper()}] LLM auth failed (401) — LLM_API_KEY is invalid or missing in .env"
            elif "429" in exc_str or "rate" in exc_str.lower():
                human_msg = f"[{self.name.upper()}] LLM rate-limited (429) — reduce concurrency or upgrade plan"
            elif "no_api_key" in exc_str or not exc_str.strip():
                human_msg = f"[{self.name.upper()}] LLM_API_KEY not set — add it to .env and restart"
            else:
                human_msg = f"[{self.name.upper()}] Error: {exc_str[:120]}"
            msg = f"{self.name}: {exc_str}"
            logger.error("agent_error", agent=self.name, error=exc_str)
            self._end_span(span, error=msg)
            await self._emit(state, "agent_error", {
                "agent": self.name,
                "error": human_msg,
                "duration_ms": duration,
            })
            await self._log(state, "error", human_msg)
            # Return ONLY the error delta — do NOT spread full state
            # (causes LangGraph INVALID_CONCURRENT_GRAPH_UPDATE in parallel nodes)
            return {"errors": [msg]}  # type: ignore[return-value]

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState: ...

    # ── LLM API call (OpenAI-compatible: SiliconFlow / Ollama / vLLM) ────────

    def _resolve_model(self, model: str | None) -> str:
        """Return model name: explicit override → agent default → primary model.

        Model aliases map to LiteLLM proxy model names which route to SiliconFlow:
          glm45-air-orchestrator   → THUDM/GLM-4.5-Air
          qwen3-235b-market-intel  → Qwen/Qwen3-235B-A22B
          deepseek-v3-strategic    → deepseek-ai/DeepSeek-V3
          llama31-8b-synthesis     → meta-llama/Meta-Llama-3.1-8B-Instruct
          qwen25-72b-rag           → Qwen/Qwen2.5-72B-Instruct
        """
        if model:
            return model
        s = self._settings
        overrides: dict[str, str] = {
            "orchestrator":        s.orchestrator_model    or s.claude_haiku_model,
            "market_intelligence": s.market_intel_model    or s.claude_model,
            "risk_assessment":     s.risk_model            or s.claude_model,
            "financial_reasoning": s.financial_model_name  or s.claude_model,
            "competitor_analysis": s.competitor_model      or s.claude_model,
            "synthesis":           s.synthesis_model       or s.claude_model,
        }
        return overrides.get(self.name, s.claude_model)

    def _get_api_key(self) -> str:
        """Return the LLM auth key.

        Priority:
          1. llm_api_key  — LiteLLM master key in production (sk-asis-...)
          2. litellm_master_key — explicit litellm key setting
          3. anthropic_api_key — legacy fallback
        """
        key = self._settings.llm_api_key.get_secret_value()
        if key:
            return key
        litellm_key = self._settings.litellm_master_key.get_secret_value()
        if litellm_key and litellm_key != "sk-asis-litellm-master-key-32c":
            return litellm_key
        return self._settings.anthropic_api_key.get_secret_value()

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, int]:
        """Call OpenAI-compatible API (SiliconFlow/Ollama/vLLM). Returns (content, total_tokens)."""
        _model = self._resolve_model(model)
        _max_tokens = max_tokens or self._settings.claude_max_tokens
        api_key = self._get_api_key()

        url = self._settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": _model,
            "max_tokens": _max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        # Rate-limit-aware retry loop — handles Groq 429 with exponential backoff
        max_attempts = 5
        for attempt in range(max_attempts):
            async with _LLM_SEMAPHORE:
                async with httpx.AsyncClient(timeout=self._settings.agent_timeout_seconds) as client:
                    resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 429:
                wait_sec = min(5 * (2 ** attempt), 60)  # 5s, 10s, 20s, 40s, 60s
                logger.warning(
                    "llm_rate_limited",
                    agent=self.name,
                    attempt=attempt + 1,
                    wait_sec=wait_sec,
                    model=_model,
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(wait_sec)
                    continue
                # All retries exhausted
                resp.raise_for_status()

            if not resp.is_success:
                try:
                    error_body = resp.json()
                except Exception:
                    error_body = resp.text
                logger.error(
                    "llm_api_error",
                    agent=self.name,
                    status_code=resp.status_code,
                    model=_model,
                    url=url,
                    error=error_body,
                )
                resp.raise_for_status()

            data = resp.json()
            content: str = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            total_tokens: int = int(usage.get("prompt_tokens", 0)) + int(usage.get("completion_tokens", 0))
            return content, total_tokens

        raise RuntimeError(f"{self.name}: exceeded max LLM retry attempts due to rate limiting")

    async def _call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        model: str | None = None,
        max_retries: int | None = None,
    ) -> tuple[T, int]:
        retries = max_retries if max_retries is not None else self._settings.max_agent_retries
        last_error = ""
        total_tokens = 0
        for attempt in range(retries + 1):
            suffix = f"\n\nFIX THIS VALIDATION ERROR:\n{last_error}" if attempt > 0 else ""
            text, tokens = await self._call_llm(system_prompt, user_prompt + suffix, model=model)
            total_tokens += tokens
            clean = text.strip()
            # Strip markdown code fences if present
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            try:
                return schema.model_validate(json.loads(clean)), total_tokens
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "llm_json_retry",
                    agent=self.name,
                    attempt=attempt,
                    error=last_error,
                )
                if attempt < retries:
                    await asyncio.sleep(1)
        raise ValueError(
            f"{self.name}: invalid JSON after {retries + 1} attempts. {last_error}"
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_tenant_id(self, state: AgentState) -> str:
        return str(
            state.get("tenant_id")
            or state.get("metadata", {}).get("tenant_id", self._settings.default_tenant_id)
        )

    def _accumulate_tokens(self, state: AgentState, new_tokens: int) -> dict[str, Any]:
        """Update metadata with total tokens and per-agent token count."""
        meta = dict(state.get("metadata", {}))
        meta["total_tokens"] = int(meta.get("total_tokens", 0)) + new_tokens
        # Per-agent token tracking (used by _persist_results in analysis.py)
        meta[f"_tokens_{self.name}"] = int(meta.get(f"_tokens_{self.name}", 0)) + new_tokens
        # Preserve token_usage dict for DB persistence
        token_usage = dict(meta.get("token_usage", {}))
        token_usage[self.name] = token_usage.get(self.name, 0) + new_tokens
        meta["token_usage"] = token_usage
        return meta

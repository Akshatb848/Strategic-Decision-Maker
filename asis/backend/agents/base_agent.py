"""
ASIS v3.0 — BaseAgent ABC.
All LLM calls via LiteLLM proxy. Every run wrapped in a Langfuse trace span.
"""
from __future__ import annotations
import asyncio, json, time
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, TypeVar
import httpx
from pydantic import BaseModel
from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.graph.state import AgentState

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)
_SSECallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]

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

    async def execute(self, state: AgentState) -> AgentState:
        start_ms = int(time.time() * 1000)
        analysis_id = state.get("analysis_id", "unknown")
        trace_id = str(state.get("metadata", {}).get("trace_id", analysis_id))
        span = self._start_span(trace_id, {"agent": self.name})
        await self._emit(state, "agent_start", {"agent": self.name, "analysis_id": analysis_id})
        logger.info("agent_start", agent=self.name, analysis_id=analysis_id)
        try:
            updated = await self.run(state)
            duration = int(time.time() * 1000) - start_ms
            tokens = updated.get("metadata", {}).get("total_tokens", 0)
            await self._emit(updated, "agent_complete", {"agent": self.name, "duration_ms": duration})
            logger.info("agent_complete", agent=self.name, duration_ms=duration)
            self._end_span(span, tokens=tokens)
            return updated
        except Exception as exc:
            duration = int(time.time() * 1000) - start_ms
            msg = f"{self.name}: {exc}"
            logger.error("agent_error", agent=self.name, error=str(exc))
            self._end_span(span, error=msg)
            await self._emit(state, "agent_error", {"agent": self.name, "error": str(exc), "duration_ms": duration})
            # Return only the delta — do NOT spread full state (causes LangGraph
            # INVALID_CONCURRENT_GRAPH_UPDATE when parallel nodes all return query/etc.)
            return {"errors": [msg]}  # type: ignore[return-value]

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState: ...

    async def _call_llm(self, system_prompt: str, user_prompt: str, model: str | None = None, max_tokens: int | None = None, temperature: float = 0.3) -> tuple[str, int]:
        _model = model or self._settings.claude_model
        _max_tokens = max_tokens or self._settings.claude_max_tokens
        # Call Anthropic API directly — bypasses the LiteLLM proxy to save ~400 MB RAM
        # on the 1 GB e2-micro instance. Uses the native Anthropic Messages API format.
        async with httpx.AsyncClient(timeout=self._settings.agent_timeout_seconds) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._settings.anthropic_api_key.get_secret_value(),
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _model,
                    "max_tokens": _max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
        content: str = data["content"][0]["text"]
        usage = data.get("usage", {})
        total_tokens: int = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return content, total_tokens

    async def _call_llm_json(self, system_prompt: str, user_prompt: str, schema: type[T], model: str | None = None, max_retries: int | None = None) -> tuple[T, int]:
        retries = max_retries if max_retries is not None else self._settings.max_agent_retries
        last_error = ""
        total_tokens = 0
        for attempt in range(retries + 1):
            suffix = f"\n\nFIX THIS ERROR:\n{last_error}" if attempt > 0 else ""
            text, tokens = await self._call_llm(system_prompt, user_prompt + suffix, model=model)
            total_tokens += tokens
            clean = text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            try:
                return schema.model_validate(json.loads(clean)), total_tokens
            except Exception as exc:
                last_error = str(exc)
                logger.warning("llm_json_retry", agent=self.name, attempt=attempt, error=last_error)
                if attempt < retries:
                    await asyncio.sleep(1)
        raise ValueError(f"{self.name}: invalid JSON after {retries + 1} attempts. {last_error}")

    async def _emit(self, state: AgentState, event: str, data: dict[str, Any]) -> None:
        cb: _SSECallback | None = state.get("metadata", {}).get("sse_callback")
        if cb:
            try:
                await cb(event, data)
            except Exception:
                pass

    def _get_tenant_id(self, state: AgentState) -> str:
        return str(state.get("tenant_id") or state.get("metadata", {}).get("tenant_id", self._settings.default_tenant_id))

    def _accumulate_tokens(self, state: AgentState, new_tokens: int) -> dict[str, Any]:
        meta = dict(state.get("metadata", {}))
        meta["total_tokens"] = int(meta.get("total_tokens", 0)) + new_tokens
        return meta

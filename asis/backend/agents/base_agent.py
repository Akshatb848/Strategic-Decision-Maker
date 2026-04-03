"""
BaseAgent — abstract base class for all ASIS specialist agents.

Every agent inherits from this class and implements `run()`.
Provides:
- Shared Anthropic client (adaptive thinking on claude-opus-4-6)
- Structured JSON output with up to 2 auto-retries on validation failure
- Token usage tracking
- Timing and error accumulation into AgentState
- SSE event emission via optional callback in state metadata
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Callable

import anthropic
from pydantic import BaseModel, ValidationError

from ..config import get_logger, get_settings
from ..graph.state import AgentState

settings = get_settings()
logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base for all six ASIS agents."""

    #: Subclasses must declare their unique name (matches DB agent_name)
    name: str = "base_agent"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    # ── Public interface ───────────────────────────────────────────────────

    async def execute(self, state: AgentState) -> AgentState:
        """
        Entry point called by LangGraph.
        Wraps run() with timing, error handling, and SSE emission.
        """
        start_ms = int(time.time() * 1000)
        await self._emit(state, "agent_start", {"agent": self.name})

        try:
            state = await self.run(state)
            duration_ms = int(time.time() * 1000) - start_ms
            await self._emit(
                state,
                "agent_complete",
                {"agent": self.name, "duration_ms": duration_ms},
            )
        except Exception as exc:
            error_msg = f"[{self.name}] {type(exc).__name__}: {exc}"
            logger.error("agent_error", agent=self.name, error=str(exc))
            state.setdefault("errors", []).append(error_msg)
            await self._emit(state, "agent_error", {"agent": self.name, "error": error_msg})

        return state

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Agent-specific logic. Must update and return the state."""

    # ── Helpers for subclasses ─────────────────────────────────────────────

    async def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
    ) -> tuple[str, int]:
        """
        Call claude-opus-4-6 with adaptive thinking and streaming.
        Returns (raw_text, tokens_used).
        """
        max_tok = max_tokens or settings.claude_max_tokens
        full_text = ""
        total_tokens = 0

        async with self._client.messages.stream(
            model=settings.claude_model,
            max_tokens=max_tok,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
            final = await stream.get_final_message()
            total_tokens = (
                final.usage.input_tokens + final.usage.output_tokens
                if final.usage
                else 0
            )

        return full_text, total_tokens

    async def _call_claude_json(
        self,
        system_prompt: str,
        user_message: str,
        schema: type[BaseModel],
        *,
        max_tokens: int | None = None,
        retries: int = 2,
    ) -> tuple[BaseModel, int]:
        """
        Call Claude, parse the response as JSON, validate against schema.
        Retries up to `retries` times on parse/validation failure.
        Returns (validated_model, tokens_used).
        """
        last_error: Exception | None = None
        accumulated_tokens = 0

        for attempt in range(retries + 1):
            retry_note = (
                f"\n\nIMPORTANT: Your previous attempt failed with: {last_error}. "
                "Fix the JSON and try again."
                if attempt > 0
                else ""
            )
            text, tokens = await self._call_claude(
                system_prompt,
                user_message + retry_note,
                max_tokens=max_tokens,
            )
            accumulated_tokens += tokens

            try:
                # Strip markdown fences if present
                clean = text.strip()
                if clean.startswith("```"):
                    clean = clean.split("```", 2)[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                    clean = clean.rsplit("```", 1)[0].strip()

                data = json.loads(clean)
                model_instance = schema.model_validate(data)
                return model_instance, accumulated_tokens

            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "json_parse_retry",
                    agent=self.name,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt == retries:
                    raise ValueError(
                        f"[{self.name}] JSON validation failed after {retries + 1} attempts: {exc}"
                    ) from exc

        raise RuntimeError("Unreachable")  # pragma: no cover

    def _update_token_usage(self, state: AgentState, tokens: int) -> None:
        """Accumulate token usage into state metadata."""
        metadata = state.setdefault("metadata", {})
        metadata.setdefault("token_usage", {})
        metadata["token_usage"][self.name] = tokens
        metadata["token_usage"]["total"] = sum(metadata["token_usage"].values())

    async def _emit(
        self,
        state: AgentState,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Send an SSE event via the optional callback stored in state.metadata."""
        callback: Callable | None = (
            state.get("metadata", {}).get("sse_callback")
        )
        if callback is not None:
            try:
                await callback(event_type, payload)
            except Exception as exc:
                logger.warning("sse_emit_failed", event=event_type, error=str(exc))

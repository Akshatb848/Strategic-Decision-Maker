"""
ASIS v3.0 — Mem0 episodic memory client.
Stores and retrieves cross-session analysis context per tenant/company.
Gracefully degrades (returns empty) if Mem0 is unavailable.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings

logger = get_logger(__name__)


def _namespace(tenant_id: str) -> str:
    return f"asis://tenant/{tenant_id}/"


class Mem0Client:
    """
    Async Mem0 client — cloud or self-hosted.

    Lookup: Orchestrator calls search() before each analysis.
    Write:  Synthesis calls add() after each completed analysis.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.mem0_api_key.get_secret_value()
        self._base_url = settings.mem0_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Token {self._api_key}"
        return headers

    async def search(
        self,
        query: str,
        tenant_id: str,
        company_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search episodic memory for past analyses on the same company/sector.

        Returns list of memory objects [{memory, metadata, score}].
        Returns empty list on any failure.
        """
        user_id = f"{_namespace(tenant_id)}{company_name.lower().replace(' ', '_')}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/memories/search/",
                    headers=self._headers(),
                    json={
                        "query": query,
                        "user_id": user_id,
                        "limit": limit,
                    },
                )
                if resp.status_code in (401, 403, 404):
                    return []
                resp.raise_for_status()
                results: list[dict[str, Any]] = resp.json().get("results", [])
                logger.debug(
                    "mem0_search",
                    company=company_name,
                    hits=len(results),
                    user_id=user_id,
                )
                return results
        except Exception as exc:
            logger.warning(
                "mem0_search_failed",
                error=str(exc),
                company=company_name,
            )
            return []

    async def add(
        self,
        memory_text: str,
        tenant_id: str,
        company_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store an analysis summary in episodic memory.

        Returns True on success, False on failure.
        """
        user_id = f"{_namespace(tenant_id)}{company_name.lower().replace(' ', '_')}"
        meta = metadata or {}
        meta.update({"tenant_id": tenant_id, "company": company_name})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/memories/",
                    headers=self._headers(),
                    json={
                        "messages": [
                            {"role": "assistant", "content": memory_text}
                        ],
                        "user_id": user_id,
                        "metadata": meta,
                    },
                )
                if resp.status_code in (401, 403):
                    return False
                resp.raise_for_status()
                logger.info(
                    "mem0_add",
                    company=company_name,
                    tenant_id=tenant_id,
                )
                return True
        except Exception as exc:
            logger.warning(
                "mem0_add_failed",
                error=str(exc),
                company=company_name,
            )
            return False

    def format_context(self, memories: list[dict[str, Any]]) -> str:
        """Format Mem0 search results into a concise context string for agents."""
        if not memories:
            return ""
        lines = ["## Prior ASIS Analyses (from memory):"]
        for m in memories[:3]:  # limit to top 3
            text = m.get("memory", "")
            if text:
                lines.append(f"- {text[:300]}")
        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_mem0_client() -> Mem0Client:
    return Mem0Client()

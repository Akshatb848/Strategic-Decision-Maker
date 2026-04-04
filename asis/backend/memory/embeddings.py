"""
ASIS v3.0 — Text embeddings via LiteLLM proxy.
All embedding calls route through LiteLLM — never directly to OpenAI/Anthropic.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings

logger = get_logger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small


async def embed_texts(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """
    Embed a batch of texts via LiteLLM proxy.

    Returns a list of float vectors, one per input text.
    Falls back to zero-vectors on error (graceful degradation).
    """
    settings = get_settings()
    _model = model or settings.embedding_model

    if not texts:
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.litellm_proxy_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.litellm_master_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json={"model": _model, "input": texts},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            embeddings = [item["embedding"] for item in data["data"]]
            logger.debug(
                "embeddings_generated",
                count=len(embeddings),
                model=_model,
                dim=len(embeddings[0]) if embeddings else 0,
            )
            return embeddings
    except Exception as exc:
        logger.warning(
            "embedding_failed",
            error=str(exc),
            model=_model,
            text_count=len(texts),
        )
        # Return zero vectors so downstream RAG degrades gracefully
        return [[0.0] * EMBEDDING_DIM for _ in texts]


async def embed_single(text: str, model: str | None = None) -> list[float]:
    """Embed a single text string. Convenience wrapper."""
    results = await embed_texts([text], model=model)
    return results[0] if results else [0.0] * EMBEDDING_DIM

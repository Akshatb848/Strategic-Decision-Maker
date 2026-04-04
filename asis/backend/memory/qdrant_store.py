"""
ASIS v3.0 — Qdrant vector store client.
Handles RAG retrieval and document ingestion.
Collections are tenant-scoped: tenant_{tenant_id}_{doc_type}
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.memory.embeddings import embed_single, embed_texts

logger = get_logger(__name__)

_FALLBACK = "DATA_UNAVAILABLE: Qdrant retrieval failed"


@dataclass
class QdrantDocument:
    """A document chunk stored in Qdrant."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class QdrantStore:
    """
    Async Qdrant client for ASIS.

    All methods are safe to call even if Qdrant is unavailable —
    they return empty results rather than raising exceptions.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.qdrant_url.rstrip("/")
        self._api_key = settings.qdrant_api_key.get_secret_value()
        self._top_k = settings.qdrant_top_k
        self._threshold = settings.qdrant_score_threshold

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key
        return headers

    def _collection_name(self, tenant_id: str, doc_type: str = "internal_docs") -> str:
        return f"tenant_{tenant_id}_{doc_type}"

    async def _ensure_collection(
        self, collection: str, client: httpx.AsyncClient
    ) -> None:
        """Create collection if it does not exist."""
        try:
            resp = await client.get(
                f"{self._base_url}/collections/{collection}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                await client.put(
                    f"{self._base_url}/collections/{collection}",
                    headers=self._headers(),
                    json={
                        "vectors": {
                            "size": 1536,
                            "distance": "Cosine",
                        }
                    },
                )
                logger.info("qdrant_collection_created", collection=collection)
        except Exception as exc:
            logger.warning("qdrant_ensure_collection_failed", error=str(exc))

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        doc_type: str = "internal_docs",
        top_k: int | None = None,
        score_threshold: float | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[QdrantDocument]:
        """
        Retrieve top-K relevant document chunks for a query.

        Returns empty list on any failure (graceful degradation).
        """
        k = top_k or self._top_k
        threshold = score_threshold or self._threshold
        collection = self._collection_name(tenant_id, doc_type)

        query_vector = await embed_single(query)
        if all(v == 0.0 for v in query_vector):
            logger.warning("qdrant_retrieve_skipped_zero_vector", query=query[:80])
            return []

        payload: dict[str, Any] = {
            "vector": query_vector,
            "limit": k,
            "score_threshold": threshold,
            "with_payload": True,
        }
        if filter_metadata:
            payload["filter"] = {
                "must": [
                    {"key": k, "match": {"value": v}}
                    for k, v in filter_metadata.items()
                ]
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._base_url}/collections/{collection}/points/search",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                results = resp.json().get("result", [])
                docs = [
                    QdrantDocument(
                        id=str(hit["id"]),
                        text=hit.get("payload", {}).get("text", ""),
                        metadata=hit.get("payload", {}),
                        score=hit.get("score", 0.0),
                    )
                    for hit in results
                ]
                logger.debug(
                    "qdrant_retrieve",
                    collection=collection,
                    hits=len(docs),
                    query=query[:60],
                )
                return docs
        except Exception as exc:
            logger.warning(
                "qdrant_retrieve_failed",
                collection=collection,
                error=str(exc),
            )
            return []

    async def upsert(
        self,
        texts: list[str],
        metadata_list: list[dict[str, Any]],
        tenant_id: str,
        doc_type: str = "internal_docs",
    ) -> int:
        """
        Embed and upsert document chunks to Qdrant.

        Returns number of chunks successfully upserted.
        """
        if not texts:
            return 0

        collection = self._collection_name(tenant_id, doc_type)
        vectors = await embed_texts(texts)

        points = []
        for i, (text, vector, meta) in enumerate(
            zip(texts, vectors, metadata_list)
        ):
            payload = {**meta, "text": text, "tenant_id": tenant_id}
            points.append(
                {
                    "id": str(uuid.uuid4()),
                    "vector": vector,
                    "payload": payload,
                }
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await self._ensure_collection(collection, client)
                resp = await client.put(
                    f"{self._base_url}/collections/{collection}/points",
                    headers=self._headers(),
                    json={"points": points},
                )
                resp.raise_for_status()
                logger.info(
                    "qdrant_upsert",
                    collection=collection,
                    chunks=len(points),
                )
                return len(points)
        except Exception as exc:
            logger.error(
                "qdrant_upsert_failed",
                collection=collection,
                error=str(exc),
            )
            return 0

    async def health_check(self) -> bool:
        """Return True if Qdrant is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/healthz")
                return resp.status_code == 200
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_qdrant_store() -> QdrantStore:
    return QdrantStore()

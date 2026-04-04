"""
POST /v1/knowledge — accepts file upload OR URL, chunks text (1000 chars, 200 overlap),
embeds via LiteLLM, upserts to Qdrant. Returns KnowledgeIngestResponse.
"""

from __future__ import annotations

import io
import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ...config import get_logger, get_settings
from ...memory.qdrant_store import QdrantStore
from ..auth import get_current_user_id
from ..schemas import KnowledgeIngestResponse

router = APIRouter(tags=["Knowledge"])
settings = get_settings()
logger = get_logger(__name__)

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks.

    Uses character-level sliding window with `overlap` characters of context
    carried forward into each subsequent chunk.
    """
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
        if start >= text_len:
            break

    return chunks


async def _fetch_url_content(url: str) -> str:
    """Fetch plain text or HTML content from a URL, stripping HTML tags."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ASIS-KnowledgeIngestor/3.0"})
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # Strip HTML tags if HTML content
            if "html" in content_type:
                import re
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

            return text
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to fetch URL: {exc}",
        ) from exc


async def _extract_file_text(file: UploadFile) -> str:
    """Extract plain text from uploaded file. Supports .txt, .md, .pdf (basic)."""
    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".pdf"):
        try:
            import pypdf  # type: ignore[import]
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            # Fall through to raw decode if pypdf not installed
            pass
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"PDF extraction failed: {exc}",
            ) from exc

    # Default: decode as UTF-8 text
    try:
        return content.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot decode file as text: {exc}",
        ) from exc


@router.post(
    "/knowledge",
    response_model=KnowledgeIngestResponse,
    summary="Ingest document into Qdrant knowledge base",
    description=(
        "Accepts a file upload OR a URL. Chunks the text (1000 chars, 200 overlap), "
        "embeds via LiteLLM, and upserts to the tenant-scoped Qdrant collection."
    ),
)
async def ingest_knowledge(
    user_id: uuid.UUID = Depends(get_current_user_id),
    file: UploadFile | None = File(default=None, description="Document file to ingest (.txt, .md, .pdf)"),
    url: str = Form(default="", description="Public URL to fetch and ingest"),
    doc_type: str = Form(default="general", description="Document type for collection routing"),
    sector: str = Form(default="", description="Industry sector tag"),
    geography: str = Form(default="", description="Geography tag"),
    source_label: str = Form(default="", description="Human-readable source label"),
    tenant_id: str = Form(default="", description="Tenant ID override (defaults to user's tenant)"),
) -> KnowledgeIngestResponse:
    """
    Ingest a document into the Qdrant knowledge base.

    Processing pipeline:
    1. Read file bytes or fetch URL
    2. Extract plain text
    3. Chunk text (1000 chars, 200 overlap)
    4. Embed each chunk via LiteLLM
    5. Upsert to Qdrant tenant collection
    """
    if not file and not url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'file' or 'url' must be provided",
        )

    # Resolve tenant
    _tenant_id = tenant_id.strip() or settings.default_tenant_id

    # Extract text
    if file:
        raw_text = await _extract_file_text(file)
        source = file.filename or "uploaded_file"
    else:
        raw_text = await _fetch_url_content(url)
        source = url

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted text is empty — nothing to ingest",
        )

    # Chunk
    chunks = _chunk_text(raw_text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text chunking produced no output",
        )

    # Build metadata list for Qdrant payloads
    metadata_list: list[dict[str, Any]] = [
        {
            "source": source,
            "doc_type": doc_type,
            "sector": sector,
            "geography": geography,
            "source_label": source_label,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "tenant_id": _tenant_id,
        }
        for i in range(len(chunks))
    ]

    # Upsert to Qdrant
    store = QdrantStore()
    inserted = await store.upsert(
        texts=chunks,
        metadata_list=metadata_list,
        tenant_id=_tenant_id,
        doc_type=doc_type,
    )

    collection = store._collection_name(_tenant_id, doc_type)
    logger.info(
        "knowledge_ingested",
        source=source,
        chunks=inserted,
        collection=collection,
        tenant_id=_tenant_id,
    )

    return KnowledgeIngestResponse(
        chunks_created=inserted,
        collection=collection,
        tenant_id=_tenant_id,
        doc_type=doc_type,
        message=f"Successfully ingested {inserted} chunks from '{source}' into collection '{collection}'",
    )

"""
POST /v1/webhooks/n8n — receives N8nTriggerPayload, verifies HMAC-SHA256 signature
(X-N8N-Signature header), queues Celery task, returns N8nTriggerResponse.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from ...config import get_logger, get_settings
from ..schemas import N8nTriggerPayload, N8nTriggerResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
settings = get_settings()
logger = get_logger(__name__)


def _verify_n8n_signature(body: bytes, signature_header: str | None) -> bool:
    """
    Verify HMAC-SHA256 signature from n8n.

    n8n sends: X-N8N-Signature: sha256=<hex_digest>
    We verify against settings.n8n_webhook_secret.
    """
    if not signature_header:
        return False

    secret = settings.n8n_webhook_secret.get_secret_value().encode()
    expected_sig = hmac.new(secret, body, hashlib.sha256).hexdigest()

    # Header format: "sha256=<hex>"
    if signature_header.startswith("sha256="):
        received_sig = signature_header[7:]
    else:
        received_sig = signature_header

    return hmac.compare_digest(expected_sig, received_sig)


@router.post(
    "/n8n",
    response_model=N8nTriggerResponse,
    summary="Receive n8n automation trigger",
    description=(
        "Receives a signed webhook from n8n, verifies HMAC-SHA256 signature, "
        "and queues the ASIS pipeline as a Celery task."
    ),
)
async def n8n_webhook(
    request: Request,
) -> N8nTriggerResponse:
    """
    Accept a trigger from n8n workflows.

    Security: verifies X-N8N-Signature (HMAC-SHA256) before processing.
    The Celery task runs the full ASIS pipeline asynchronously.
    """
    # Read raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-N8N-Signature")

    # Verify signature — reject if invalid
    if not _verify_n8n_signature(body, signature):
        logger.warning(
            "n8n_webhook_invalid_signature",
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    import json
    try:
        raw_payload: dict[str, Any] = json.loads(body)
        payload = N8nTriggerPayload(**raw_payload)
    except Exception as exc:
        logger.warning("n8n_webhook_parse_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payload: {exc}",
        ) from exc

    analysis_id = str(uuid.uuid4())

    # Queue Celery task
    try:
        from ...tasks.pipeline import run_analysis_task  # type: ignore[import]

        run_analysis_task.apply_async(
            kwargs={
                "analysis_id": analysis_id,
                "query": payload.query,
                "company_context": payload.company_context.model_dump(),
                "options": payload.options.model_dump(),
                "tenant_id": payload.tenant_id or settings.default_tenant_id,
                "callback_url": payload.callback_url,
                "trigger_source": "n8n_webhook",
                "workflow_id": payload.workflow_id,
                "workflow_name": payload.workflow_name,
            },
            task_id=analysis_id,
        )
        logger.info(
            "n8n_webhook_queued",
            analysis_id=analysis_id,
            workflow_id=payload.workflow_id,
            tenant_id=payload.tenant_id,
        )
    except ImportError:
        # Celery not configured — log and continue (dev mode)
        logger.warning(
            "n8n_webhook_celery_unavailable",
            analysis_id=analysis_id,
            note="Celery tasks module not imported; running in dev mode",
        )
    except Exception as exc:
        logger.error("n8n_webhook_queue_error", analysis_id=analysis_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue analysis task",
        ) from exc

    return N8nTriggerResponse(
        analysis_id=analysis_id,
        status="queued",
        message=f"Analysis queued successfully for workflow '{payload.workflow_name}'",
    )

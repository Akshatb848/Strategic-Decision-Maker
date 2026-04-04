"""
ASIS v3.0 — Celery application with Redis Streams (Memorystore in production).
"""
from __future__ import annotations
from celery import Celery
from asis.backend.config.settings import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery("asis")
    app.config_from_object({
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "task_acks_late": True,
        "worker_prefetch_multiplier": 1,
        "broker_transport_options": {"visibility_timeout": 3600},
    })
    app.autodiscover_tasks(["asis.backend.tasks"])
    return app


celery_app = create_celery_app()

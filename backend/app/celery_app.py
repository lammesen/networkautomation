"""Celery application configuration."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def _ensure_rediss_ssl(url: str) -> str:
    """If using rediss:// and no ssl_cert_reqs is provided, add a safe default."""
    if not url or not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    if parsed.query and "ssl_cert_reqs" in parsed.query:
        return url
    query = "ssl_cert_reqs=CERT_NONE" if parsed.query == "" else f"{parsed.query}&ssl_cert_reqs=CERT_NONE"
    return urlunparse(parsed._replace(query=query))


broker_url = _ensure_rediss_ssl(settings.celery_broker_url)
result_backend = _ensure_rediss_ssl(settings.celery_result_backend)

celery_app = Celery(
    "network_automation",
    broker=broker_url,
    backend=result_backend,
    include=[
        "app.jobs.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "scheduled-config-backup": {
            "task": "scheduled_config_backup",
            "schedule": crontab(hour=2, minute=0),
        },
        "check-reachability": {
            "task": "check_reachability_job",
            "schedule": 60.0,
        },
    },
)


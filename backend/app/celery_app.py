"""Celery application configuration."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def _ensure_rediss_ssl(url: str, environment: str = "production") -> str:
    """If using rediss:// and no ssl_cert_reqs is provided, add a safe default based on environment."""
    if not url or not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    if parsed.query and "ssl_cert_reqs" in parsed.query:
        return url
    # Use CERT_NONE only in development, CERT_REQUIRED otherwise
    cert_reqs = (
        "CERT_NONE" if environment.lower() in ("development", "dev", "local") else "CERT_REQUIRED"
    )
    query = (
        f"ssl_cert_reqs={cert_reqs}"
        if parsed.query == ""
        else f"{parsed.query}&ssl_cert_reqs={cert_reqs}"
    )
    return urlunparse(parsed._replace(query=query))


# Determine environment from settings
environment = getattr(settings, "environment", "production")
broker_url = _ensure_rediss_ssl(settings.celery_broker_url, environment)
result_backend = _ensure_rediss_ssl(settings.celery_result_backend, environment)

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

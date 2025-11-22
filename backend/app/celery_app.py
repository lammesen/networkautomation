"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "network_automation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
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



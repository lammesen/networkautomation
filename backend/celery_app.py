from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery = Celery(
    "netauto",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.task_routes = {
    "app.jobs.tasks.*": {"queue": "jobs"},
}

if settings.enable_celery_beat:
    celery.conf.beat_schedule = {
        "nightly-backup": {
            "task": "app.jobs.tasks.schedule_nightly_backup",
            "schedule": crontab.fromstring(settings.celery_backup_schedule_cron),
        }
    }

celery.autodiscover_tasks(["app.jobs"])

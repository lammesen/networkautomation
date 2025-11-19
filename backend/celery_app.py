from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery = Celery(
    "netauto",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.task_routes = {
    "app.jobs.tasks.*": {"queue": "jobs"},
}

celery.autodiscover_tasks(["app.jobs"])

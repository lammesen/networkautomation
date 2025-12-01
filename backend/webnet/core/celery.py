"""Celery application for webnet."""

from __future__ import annotations

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webnet.settings")

celery_app = Celery("webnet")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()

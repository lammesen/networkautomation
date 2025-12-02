from __future__ import annotations

from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.workflows"
    verbose_name = "Automation Workflows"

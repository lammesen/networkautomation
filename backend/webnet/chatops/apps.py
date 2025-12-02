"""ChatOps app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class ChatopsConfig(AppConfig):
    """ChatOps app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.chatops"
    verbose_name = "ChatOps Integration"

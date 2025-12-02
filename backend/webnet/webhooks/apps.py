"""Django app configuration for webhooks."""

from django.apps import AppConfig


class WebhooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.webhooks"
    verbose_name = "Webhooks"

    def ready(self):
        """Import signals when app is ready."""
        import webnet.webhooks.signals  # noqa: F401

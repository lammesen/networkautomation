from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.core"
    verbose_name = "Core"

    def ready(self) -> None:
        # Import signals to register them
        import webnet.core.signals  # noqa: F401

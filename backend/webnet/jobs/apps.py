from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.jobs"
    verbose_name = "Jobs"

    def ready(self):
        import webnet.jobs.signals  # noqa: F401

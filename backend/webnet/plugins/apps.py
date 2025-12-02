"""Plugin app configuration."""

from django.apps import AppConfig


class PluginsConfig(AppConfig):
    """Configuration for the plugins app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "webnet.plugins"
    verbose_name = "Plugins"

    def ready(self) -> None:
        """Initialize plugin system when Django starts."""
        from webnet.plugins.registry import plugin_registry

        plugin_registry.discover_plugins()

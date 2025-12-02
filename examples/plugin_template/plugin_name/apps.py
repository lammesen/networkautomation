"""Django app configuration."""

from django.apps import AppConfig


class PluginNameConfig(AppConfig):
    """Configuration for the plugin."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "plugin_name"
    verbose_name = "Plugin Name"

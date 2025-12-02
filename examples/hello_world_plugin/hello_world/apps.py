"""Django app configuration for Hello World plugin."""

from django.apps import AppConfig


class HelloWorldConfig(AppConfig):
    """Configuration for Hello World plugin."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "hello_world"
    verbose_name = "Hello World Plugin"

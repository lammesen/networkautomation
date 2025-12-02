"""Base plugin class and interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model
    from rest_framework.viewsets import ViewSet


class PluginBase(ABC):
    """Base class for all webnet plugins.

    Plugins should inherit from this class and implement the required methods.
    """

    # Required metadata
    name: str = ""  # Unique plugin identifier
    verbose_name: str = ""  # Human-readable name
    description: str = ""  # Plugin description
    version: str = "0.1.0"  # Plugin version
    author: str = ""  # Plugin author

    # Optional metadata
    min_webnet_version: str = ""  # Minimum compatible webnet version
    max_webnet_version: str = ""  # Maximum compatible webnet version
    dependencies: list[str] = []  # List of required plugin names

    def __init__(self) -> None:
        """Initialize the plugin."""
        self.validate_metadata()

    def validate_metadata(self) -> None:
        """Validate that required metadata is provided."""
        if not self.name:
            raise ValueError(f"Plugin {self.__class__.__name__} must define 'name'")
        if not self.verbose_name:
            raise ValueError(f"Plugin {self.__class__.__name__} must define 'verbose_name'")
        if not self.version:
            raise ValueError(f"Plugin {self.__class__.__name__} must define 'version'")

    def get_models(self) -> list[type[Model]]:
        """Return list of Django models provided by this plugin.

        Returns:
            List of Django model classes
        """
        return []

    def get_api_viewsets(self) -> list[tuple[str, type[ViewSet], str]]:
        """Return list of API viewsets provided by this plugin.

        Returns:
            List of tuples: (url_prefix, viewset_class, basename)
            Example: [("widgets", WidgetViewSet, "widget")]
        """
        return []

    def get_ui_views(self) -> list[tuple[str, Any]]:
        """Return list of UI views provided by this plugin.

        Returns:
            List of tuples: (url_pattern, view)
            Example: [("widgets/", widget_list_view)]
        """
        return []

    def get_navigation_items(self) -> list[dict[str, Any]]:
        """Return navigation items to add to the UI.

        Returns:
            List of navigation item dicts with keys: label, url, icon, order
            Example: [{"label": "Widgets", "url": "/widgets/", "icon": "puzzle", "order": 100}]
        """
        return []

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return dashboard widgets to display.

        Returns:
            List of widget dicts with keys: title, template, order, permissions
            Example: [{"title": "My Widget", "template": "myplugin/widget.html", "order": 10}]
        """
        return []

    def get_settings_schema(self) -> dict[str, Any]:
        """Return JSON schema for plugin settings.

        Returns:
            JSON schema dict defining plugin configuration options
        """
        return {}

    def on_load(self) -> None:
        """Called when plugin is loaded. Use for initialization."""
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded. Use for cleanup."""
        pass

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        pass

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        pass

    def health_check(self) -> dict[str, Any]:
        """Perform health check and return status.

        Returns:
            Dict with keys: healthy (bool), message (str), details (dict)
        """
        return {"healthy": True, "message": "OK", "details": {}}


class PluginInterface(ABC):
    """Interface for plugin extension points."""

    @abstractmethod
    def get_extension_points(self) -> dict[str, Any]:
        """Return available extension points."""
        pass

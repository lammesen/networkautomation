"""Plugin definition."""

from webnet.plugins.base import PluginBase


class Plugin(PluginBase):
    """Your plugin implementation."""

    # Required metadata
    name = "plugin_name"  # Unique identifier
    verbose_name = "Plugin Name"  # Human-readable name
    description = "Description of what your plugin does"
    version = "1.0.0"  # Semantic version
    author = "Your Name"

    # Optional metadata
    min_webnet_version = ""  # Minimum compatible webnet version (e.g., "1.0.0")
    max_webnet_version = ""  # Maximum compatible webnet version (e.g., "2.0.0")
    dependencies = []  # List of required plugin names (e.g., ["other_plugin"])

    def get_models(self):
        """Return list of Django models provided by this plugin."""
        # Example:
        # from .models import MyModel
        # return [MyModel]
        return []

    def get_api_viewsets(self):
        """Return list of API viewsets provided by this plugin."""
        # Example:
        # from .views import MyViewSet
        # return [
        #     ("my-resource", MyViewSet, "my-resource"),
        # ]
        return []

    def get_ui_views(self):
        """Return list of UI views provided by this plugin."""
        # Example:
        # from .views import my_view
        # return [
        #     ("my-page/", my_view),
        # ]
        return []

    def get_navigation_items(self):
        """Return navigation items to add to the UI."""
        # Example:
        # return [
        #     {
        #         "label": "My Page",
        #         "url": "/my-page/",
        #         "icon": "puzzle",  # Lucide icon name
        #         "order": 100,
        #     }
        # ]
        return []

    def get_dashboard_widgets(self):
        """Return dashboard widgets to display."""
        # Example:
        # return [
        #     {
        #         "title": "My Widget",
        #         "template": "plugin_name/widget.html",
        #         "order": 10,
        #         "permissions": [],  # Optional permission list
        #     }
        # ]
        return []

    def get_settings_schema(self):
        """Return JSON schema for plugin settings."""
        # Example:
        # return {
        #     "type": "object",
        #     "properties": {
        #         "api_key": {
        #             "type": "string",
        #             "title": "API Key",
        #             "description": "Your API key"
        #         },
        #         "enabled": {
        #             "type": "boolean",
        #             "title": "Enabled",
        #             "default": True
        #         }
        #     },
        #     "required": ["api_key"]
        # }
        return {}

    def on_load(self):
        """Called when plugin is loaded."""
        # Initialize resources, connections, etc.
        pass

    def on_unload(self):
        """Called when plugin is unloaded."""
        # Clean up resources
        pass

    def on_enable(self):
        """Called when plugin is enabled."""
        # Start background tasks, register signals, etc.
        pass

    def on_disable(self):
        """Called when plugin is disabled."""
        # Stop background tasks, unregister signals, etc.
        pass

    def health_check(self):
        """Perform health check and return status."""
        # Example:
        # try:
        #     # Check dependencies, connections, etc.
        #     is_healthy = self.check_connection()
        #     return {
        #         "healthy": is_healthy,
        #         "message": "Connection established" if is_healthy else "Connection failed",
        #         "details": {"status": "ok"}
        #     }
        # except Exception as e:
        #     return {
        #         "healthy": False,
        #         "message": f"Health check failed: {str(e)}",
        #         "details": {}
        #     }
        return {"healthy": True, "message": "OK", "details": {}}

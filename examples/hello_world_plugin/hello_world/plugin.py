"""Plugin definition for Hello World."""

from webnet.plugins.base import PluginBase


class Plugin(PluginBase):
    """Hello World plugin implementation."""
    
    name = "hello_world"
    verbose_name = "Hello World"
    description = "A simple example plugin demonstrating webnet plugin system capabilities"
    version = "1.0.0"
    author = "webnet Team"
    
    def get_navigation_items(self):
        """Add navigation item to the UI."""
        return [
            {
                "label": "Hello World",
                "url": "/hello-world/",
                "icon": "hand-wave",
                "order": 999,
            }
        ]
    
    def get_dashboard_widgets(self):
        """Add a dashboard widget."""
        return [
            {
                "title": "Hello World Widget",
                "template": "hello_world/widget.html",
                "order": 100,
            }
        ]
    
    def get_settings_schema(self):
        """Define plugin settings schema."""
        return {
            "type": "object",
            "properties": {
                "greeting_message": {
                    "type": "string",
                    "title": "Greeting Message",
                    "default": "Hello, World!",
                    "description": "The message to display in the greeting"
                },
                "show_timestamp": {
                    "type": "boolean",
                    "title": "Show Timestamp",
                    "default": True,
                    "description": "Whether to show the current timestamp"
                }
            }
        }
    
    def on_load(self):
        """Called when plugin is loaded."""
        print(f"[{self.name}] Plugin loaded successfully!")
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        print(f"[{self.name}] Plugin unloaded successfully!")
    
    def on_enable(self):
        """Called when plugin is enabled."""
        print(f"[{self.name}] Plugin enabled!")
    
    def on_disable(self):
        """Called when plugin is disabled."""
        print(f"[{self.name}] Plugin disabled!")
    
    def health_check(self):
        """Perform health check."""
        return {
            "healthy": True,
            "message": "Hello World plugin is running perfectly!",
            "details": {
                "version": self.version,
                "status": "operational"
            }
        }

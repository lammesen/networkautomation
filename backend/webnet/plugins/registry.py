"""Plugin registry for discovering and managing plugins."""

from __future__ import annotations

import importlib
import logging
from typing import Any, TYPE_CHECKING

from django.apps import apps
from django.conf import settings

if TYPE_CHECKING:
    from webnet.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing plugins."""
    
    def __init__(self) -> None:
        """Initialize the plugin registry."""
        self._plugins: dict[str, PluginBase] = {}
        self._loaded_plugins: set[str] = set()
    
    def discover_plugins(self) -> None:
        """Discover and register plugins from INSTALLED_APPS."""
        plugin_apps = getattr(settings, "WEBNET_PLUGINS", [])
        
        for plugin_app in plugin_apps:
            try:
                self._load_plugin_app(plugin_app)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_app}: {e}", exc_info=True)
    
    def _load_plugin_app(self, plugin_app: str) -> None:
        """Load a plugin from an app name."""
        try:
            # Try to import the plugin module
            plugin_module = importlib.import_module(f"{plugin_app}.plugin")
            
            # Look for a Plugin class
            if hasattr(plugin_module, "Plugin"):
                plugin_class = plugin_module.Plugin
                plugin = plugin_class()
                self.register_plugin(plugin)
                logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")
            else:
                logger.warning(f"Plugin app {plugin_app} has no Plugin class")
        except ImportError:
            logger.debug(f"No plugin module found in {plugin_app}")
        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_app}: {e}", exc_info=True)
    
    def register_plugin(self, plugin: PluginBase) -> None:
        """Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
        """
        if plugin.name in self._plugins:
            logger.warning(f"Plugin {plugin.name} is already registered")
            return
        
        self._plugins[plugin.name] = plugin
        logger.debug(f"Registered plugin: {plugin.name}")
    
    def get_plugin(self, name: str) -> PluginBase | None:
        """Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> dict[str, PluginBase]:
        """Get all registered plugins.
        
        Returns:
            Dictionary of plugin name to plugin instance
        """
        return self._plugins.copy()
    
    def load_plugin(self, name: str) -> bool:
        """Load a plugin and call its on_load hook.
        
        Args:
            name: Plugin name
            
        Returns:
            True if loaded successfully, False otherwise
        """
        plugin = self.get_plugin(name)
        if not plugin:
            logger.error(f"Plugin {name} not found")
            return False
        
        if name in self._loaded_plugins:
            logger.debug(f"Plugin {name} is already loaded")
            return True
        
        try:
            plugin.on_load()
            self._loaded_plugins.add(name)
            logger.info(f"Loaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}", exc_info=True)
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin and call its on_unload hook.
        
        Args:
            name: Plugin name
            
        Returns:
            True if unloaded successfully, False otherwise
        """
        plugin = self.get_plugin(name)
        if not plugin:
            logger.error(f"Plugin {name} not found")
            return False
        
        if name not in self._loaded_plugins:
            logger.debug(f"Plugin {name} is not loaded")
            return True
        
        try:
            plugin.on_unload()
            self._loaded_plugins.discard(name)
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}", exc_info=True)
            return False
    
    def is_plugin_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded.
        
        Args:
            name: Plugin name
            
        Returns:
            True if loaded, False otherwise
        """
        return name in self._loaded_plugins
    
    def get_plugin_models(self, name: str) -> list[Any]:
        """Get models provided by a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            List of model classes
        """
        plugin = self.get_plugin(name)
        if not plugin:
            return []
        return plugin.get_models()
    
    def get_plugin_viewsets(self, name: str) -> list[tuple[str, Any, str]]:
        """Get API viewsets provided by a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            List of (url_prefix, viewset_class, basename) tuples
        """
        plugin = self.get_plugin(name)
        if not plugin:
            return []
        return plugin.get_api_viewsets()
    
    def get_all_navigation_items(self) -> list[dict[str, Any]]:
        """Get navigation items from all loaded plugins.
        
        Returns:
            List of navigation item dicts
        """
        items = []
        for name in self._loaded_plugins:
            plugin = self.get_plugin(name)
            if plugin:
                items.extend(plugin.get_navigation_items())
        return sorted(items, key=lambda x: x.get("order", 100))
    
    def get_all_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Get dashboard widgets from all loaded plugins.
        
        Returns:
            List of widget dicts
        """
        widgets = []
        for name in self._loaded_plugins:
            plugin = self.get_plugin(name)
            if plugin:
                widgets.extend(plugin.get_dashboard_widgets())
        return sorted(widgets, key=lambda x: x.get("order", 100))


# Global plugin registry instance
plugin_registry = PluginRegistry()

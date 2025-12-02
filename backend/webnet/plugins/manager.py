"""Service for managing plugin operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db import transaction

from webnet.plugins.models import PluginConfig, CustomerPluginConfig, PluginAuditLog
from webnet.plugins.registry import plugin_registry

if TYPE_CHECKING:
    from webnet.customers.models import Customer
    from webnet.users.models import User

logger = logging.getLogger(__name__)


class PluginManager:
    """Service for managing plugin lifecycle and configuration."""

    @staticmethod
    def sync_plugins() -> None:
        """Sync plugin registry with database configurations."""
        for name, plugin in plugin_registry.get_all_plugins().items():
            config, created = PluginConfig.objects.get_or_create(
                name=name,
                defaults={
                    "verbose_name": plugin.verbose_name,
                    "description": plugin.description,
                    "version": plugin.version,
                    "author": plugin.author,
                    "min_webnet_version": plugin.min_webnet_version,
                    "max_webnet_version": plugin.max_webnet_version,
                    "dependencies": plugin.dependencies,
                },
            )

            if not created:
                # Update existing config if version changed
                if config.version != plugin.version:
                    config.version = plugin.version
                    config.verbose_name = plugin.verbose_name
                    config.description = plugin.description
                    config.author = plugin.author
                    config.save()

    @staticmethod
    def enable_plugin(
        plugin_name: str, customer: Customer | None = None, user: User | None = None
    ) -> tuple[bool, str]:
        """Enable a plugin globally or for a specific customer.

        Args:
            plugin_name: Name of the plugin to enable
            customer: Customer to enable for (None for global)
            user: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            config = PluginConfig.objects.get(name=plugin_name)
        except PluginConfig.DoesNotExist:
            return False, f"Plugin {plugin_name} not found"

        with transaction.atomic():
            if customer:
                # Enable for specific customer
                customer_config, _ = CustomerPluginConfig.objects.get_or_create(
                    customer=customer, plugin=config
                )
                customer_config.enabled = True
                customer_config.save()

                PluginAuditLog.objects.create(
                    plugin=config,
                    customer=customer,
                    user=user,
                    action="enable",
                    success=True,
                    details={"scope": "customer"},
                )
                message = f"Plugin {config.verbose_name} enabled for {customer.name}"
            else:
                # Enable globally
                config.enabled = True
                config.save()

                # Also load the plugin
                plugin_registry.load_plugin(plugin_name)

                # Call plugin's on_enable hook
                plugin = plugin_registry.get_plugin(plugin_name)
                if plugin:
                    try:
                        plugin.on_enable()
                    except Exception as e:
                        logger.error(f"Error in plugin on_enable: {e}", exc_info=True)

                PluginAuditLog.objects.create(
                    plugin=config,
                    user=user,
                    action="enable",
                    success=True,
                    details={"scope": "global"},
                )
                message = f"Plugin {config.verbose_name} enabled globally"

        return True, message

    @staticmethod
    def disable_plugin(
        plugin_name: str, customer: Customer | None = None, user: User | None = None
    ) -> tuple[bool, str]:
        """Disable a plugin globally or for a specific customer.

        Args:
            plugin_name: Name of the plugin to disable
            customer: Customer to disable for (None for global)
            user: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            config = PluginConfig.objects.get(name=plugin_name)
        except PluginConfig.DoesNotExist:
            return False, f"Plugin {plugin_name} not found"

        with transaction.atomic():
            if customer:
                # Disable for specific customer
                try:
                    customer_config = CustomerPluginConfig.objects.get(
                        customer=customer, plugin=config
                    )
                    customer_config.enabled = False
                    customer_config.save()
                except CustomerPluginConfig.DoesNotExist:
                    pass

                PluginAuditLog.objects.create(
                    plugin=config,
                    customer=customer,
                    user=user,
                    action="disable",
                    success=True,
                    details={"scope": "customer"},
                )
                message = f"Plugin {config.verbose_name} disabled for {customer.name}"
            else:
                # Disable globally
                config.enabled = False
                config.save()

                # Call plugin's on_disable hook
                plugin = plugin_registry.get_plugin(plugin_name)
                if plugin:
                    try:
                        plugin.on_disable()
                    except Exception as e:
                        logger.error(f"Error in plugin on_disable: {e}", exc_info=True)

                # Unload the plugin
                plugin_registry.unload_plugin(plugin_name)

                PluginAuditLog.objects.create(
                    plugin=config,
                    user=user,
                    action="disable",
                    success=True,
                    details={"scope": "global"},
                )
                message = f"Plugin {config.verbose_name} disabled globally"

        return True, message

    @staticmethod
    def is_plugin_enabled(plugin_name: str, customer: Customer | None = None) -> bool:
        """Check if a plugin is enabled.

        Args:
            plugin_name: Name of the plugin
            customer: Customer to check for (None for global)

        Returns:
            True if enabled, False otherwise
        """
        try:
            config = PluginConfig.objects.get(name=plugin_name)
        except PluginConfig.DoesNotExist:
            return False

        if not config.enabled:
            return False

        if customer:
            try:
                customer_config = CustomerPluginConfig.objects.get(customer=customer, plugin=config)
                return bool(customer_config.enabled)
            except CustomerPluginConfig.DoesNotExist:
                return True  # Default to enabled if no customer config exists

        return True

    @staticmethod
    def update_plugin_settings(
        plugin_name: str,
        settings: dict[str, Any],
        customer: Customer | None = None,
        user: User | None = None,
    ) -> tuple[bool, str]:
        """Update plugin settings.

        Args:
            plugin_name: Name of the plugin
            settings: New settings dict
            customer: Customer to update settings for (None for global)
            user: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            config = PluginConfig.objects.get(name=plugin_name)
        except PluginConfig.DoesNotExist:
            return False, f"Plugin {plugin_name} not found"

        with transaction.atomic():
            if customer:
                customer_config, _ = CustomerPluginConfig.objects.get_or_create(
                    customer=customer, plugin=config
                )
                customer_config.settings = settings
                customer_config.save()

                PluginAuditLog.objects.create(
                    plugin=config,
                    customer=customer,
                    user=user,
                    action="configure",
                    success=True,
                    details={"scope": "customer", "settings": settings},
                )
                message = f"Settings updated for {config.verbose_name} (customer: {customer.name})"
            else:
                config.settings = settings
                config.save()

                PluginAuditLog.objects.create(
                    plugin=config,
                    user=user,
                    action="configure",
                    success=True,
                    details={"scope": "global", "settings": settings},
                )
                message = f"Settings updated for {config.verbose_name} (global)"

        return True, message

    @staticmethod
    def get_plugin_health(plugin_name: str) -> dict[str, Any]:
        """Get health status of a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Health status dict
        """
        plugin = plugin_registry.get_plugin(plugin_name)
        if not plugin:
            return {"healthy": False, "message": "Plugin not found", "details": {}}

        if not plugin_registry.is_plugin_loaded(plugin_name):
            return {"healthy": False, "message": "Plugin not loaded", "details": {}}

        try:
            return plugin.health_check()
        except Exception as e:
            logger.error(f"Error checking plugin health: {e}", exc_info=True)
            return {"healthy": False, "message": f"Health check failed: {str(e)}", "details": {}}

"""Serializers for plugin API."""

from __future__ import annotations

from rest_framework import serializers

from webnet.plugins.models import PluginConfig, CustomerPluginConfig, PluginAuditLog


class PluginConfigSerializer(serializers.ModelSerializer):
    """Serializer for PluginConfig."""

    is_loaded = serializers.SerializerMethodField()
    health_status = serializers.SerializerMethodField()

    class Meta:
        model = PluginConfig
        fields = [
            "id",
            "name",
            "verbose_name",
            "description",
            "version",
            "author",
            "enabled",
            "installed_at",
            "settings",
            "min_webnet_version",
            "max_webnet_version",
            "dependencies",
            "is_loaded",
            "health_status",
        ]
        read_only_fields = [
            "id",
            "name",
            "verbose_name",
            "description",
            "version",
            "author",
            "installed_at",
            "min_webnet_version",
            "max_webnet_version",
            "dependencies",
            "is_loaded",
            "health_status",
        ]

    def get_is_loaded(self, obj: PluginConfig) -> bool:
        """Check if plugin is loaded."""
        from webnet.plugins.registry import plugin_registry

        return plugin_registry.is_plugin_loaded(obj.name)

    def get_health_status(self, obj: PluginConfig) -> dict:
        """Get plugin health status."""
        from webnet.plugins.manager import PluginManager

        if not obj.enabled:
            return {"healthy": False, "message": "Plugin disabled", "details": {}}
        return PluginManager.get_plugin_health(obj.name)


class CustomerPluginConfigSerializer(serializers.ModelSerializer):
    """Serializer for CustomerPluginConfig."""

    plugin_name = serializers.CharField(source="plugin.name", read_only=True)
    plugin_verbose_name = serializers.CharField(source="plugin.verbose_name", read_only=True)
    plugin_version = serializers.CharField(source="plugin.version", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = CustomerPluginConfig
        fields = [
            "id",
            "customer",
            "customer_name",
            "plugin",
            "plugin_name",
            "plugin_verbose_name",
            "plugin_version",
            "enabled",
            "settings",
            "enabled_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "plugin_name",
            "plugin_verbose_name",
            "plugin_version",
            "customer_name",
            "enabled_at",
            "updated_at",
        ]


class PluginAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for PluginAuditLog."""

    plugin_name = serializers.CharField(source="plugin.name", read_only=True)
    plugin_verbose_name = serializers.CharField(source="plugin.verbose_name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = PluginAuditLog
        fields = [
            "id",
            "plugin",
            "plugin_name",
            "plugin_verbose_name",
            "customer",
            "customer_name",
            "user",
            "user_username",
            "action",
            "timestamp",
            "details",
            "success",
            "error_message",
        ]
        read_only_fields = "__all__"


class PluginSettingsSerializer(serializers.Serializer):
    """Serializer for updating plugin settings."""

    settings = serializers.JSONField()

"""API views for plugin management."""

from __future__ import annotations

from typing import Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from webnet.api.permissions import RolePermission
from webnet.plugins.models import PluginConfig, CustomerPluginConfig, PluginAuditLog
from webnet.plugins.serializers import (
    PluginConfigSerializer,
    CustomerPluginConfigSerializer,
    PluginAuditLogSerializer,
    PluginSettingsSerializer,
)
from webnet.plugins.manager import PluginManager


class PluginViewSet(viewsets.ModelViewSet):
    """API viewset for managing plugins."""

    queryset = PluginConfig.objects.all()
    serializer_class = PluginConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission]

    @action(detail=True, methods=["post"])
    def enable(self, request: Any, pk: Any = None) -> Response:
        """Enable a plugin globally."""
        plugin_config = self.get_object()
        success, message = PluginManager.enable_plugin(plugin_config.name, user=request.user)

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def disable(self, request: Any, pk: Any = None) -> Response:
        """Disable a plugin globally."""
        plugin_config = self.get_object()
        success, message = PluginManager.disable_plugin(plugin_config.name, user=request.user)

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def update_settings(self, request: Any, pk: Any = None) -> Response:
        """Update plugin settings."""
        plugin_config = self.get_object()
        serializer = PluginSettingsSerializer(data=request.data)

        if serializer.is_valid():
            success, message = PluginManager.update_plugin_settings(
                plugin_config.name, serializer.validated_data["settings"], user=request.user
            )

            if success:
                return Response({"message": message}, status=status.HTTP_200_OK)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def health(self, request: Any, pk: Any = None) -> Response:
        """Get plugin health status."""
        plugin_config = self.get_object()
        health_status = PluginManager.get_plugin_health(plugin_config.name)
        return Response(health_status, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def sync(self, request: Any) -> Response:
        """Sync plugins from registry to database."""
        PluginManager.sync_plugins()
        return Response({"message": "Plugins synced successfully"}, status=status.HTTP_200_OK)


class CustomerPluginConfigViewSet(viewsets.ModelViewSet):
    """API viewset for customer-specific plugin configurations."""

    queryset = CustomerPluginConfig.objects.all()
    serializer_class = CustomerPluginConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    filterset_fields = ["customer", "plugin", "enabled"]

    def get_queryset(self) -> Any:
        """Filter by customer based on user role."""
        queryset = super().get_queryset()
        user = self.request.user

        # Admins see all
        if user.role == "admin":
            return queryset

        # Others see only their customers
        return queryset.filter(customer__in=user.customers.all())

    @action(detail=True, methods=["post"])
    def enable(self, request: Any, pk: Any = None) -> Response:
        """Enable a plugin for a customer."""
        customer_config = self.get_object()
        success, message = PluginManager.enable_plugin(
            customer_config.plugin.name, customer=customer_config.customer, user=request.user
        )

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def disable(self, request: Any, pk: Any = None) -> Response:
        """Disable a plugin for a customer."""
        customer_config = self.get_object()
        success, message = PluginManager.disable_plugin(
            customer_config.plugin.name, customer=customer_config.customer, user=request.user
        )

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def update_settings(self, request: Any, pk: Any = None) -> Response:
        """Update customer-specific plugin settings."""
        customer_config = self.get_object()
        serializer = PluginSettingsSerializer(data=request.data)

        if serializer.is_valid():
            success, message = PluginManager.update_plugin_settings(
                customer_config.plugin.name,
                serializer.validated_data["settings"],
                customer=customer_config.customer,
                user=request.user,
            )

            if success:
                return Response({"message": message}, status=status.HTTP_200_OK)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PluginAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for plugin audit logs."""

    queryset = PluginAuditLog.objects.all()
    serializer_class = PluginAuditLogSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    filterset_fields = ["plugin", "customer", "user", "action", "success"]

    def get_queryset(self) -> Any:
        """Filter by customer based on user role."""
        queryset = super().get_queryset()
        user = self.request.user

        # Admins see all
        if user.role == "admin":
            return queryset

        # Others see global logs (customer__isnull) and their customer logs
        # Using select_related for performance optimization
        return (
            queryset.filter(customer__isnull=True)
            | queryset.filter(customer__in=user.customers.all())
        ).select_related("plugin", "customer", "user")

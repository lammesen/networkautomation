"""URL configuration for plugin API."""

from rest_framework.routers import DefaultRouter

from webnet.plugins.views import (
    PluginViewSet,
    CustomerPluginConfigViewSet,
    PluginAuditLogViewSet,
)

router = DefaultRouter()
router.register(r"plugins", PluginViewSet, basename="plugin")
router.register(r"customer-plugins", CustomerPluginConfigViewSet, basename="customer-plugin")
router.register(r"plugin-audit-logs", PluginAuditLogViewSet, basename="plugin-audit-log")

urlpatterns = router.urls

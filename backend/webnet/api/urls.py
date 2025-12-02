"""API URL wiring for webnet APIs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from webnet.notifications.views import (
    SMTPConfigViewSet,
    NotificationPreferenceViewSet,
    NotificationEventViewSet,
)

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"customers", views.CustomerViewSet, basename="customer")
router.register(r"credentials", views.CredentialViewSet, basename="credential")
router.register(r"devices", views.DeviceViewSet, basename="device")
router.register(r"jobs", views.JobViewSet, basename="job")
router.register(r"jobs/admin", views.JobAdminViewSet, basename="job-admin")
router.register(r"compliance/policies", views.CompliancePolicyViewSet, basename="compliance-policy")
router.register(r"compliance/results", views.ComplianceResultViewSet, basename="compliance-result")
router.register(
    r"compliance/remediation-rules",
    views.RemediationRuleViewSet,
    basename="remediation-rule",
)
router.register(
    r"compliance/remediation-actions",
    views.RemediationActionViewSet,
    basename="remediation-action",
)
router.register(r"topology/links", views.TopologyLinkViewSet, basename="topology-link")
router.register(r"ssh/host-keys", views.SSHHostKeyViewSet, basename="ssh-host-key")
router.register(
    r"topology/discovered-devices", views.DiscoveredDeviceViewSet, basename="discovered-device"
)
# Issue #24 - Device Tags and Groups
router.register(r"tags", views.TagViewSet, basename="tag")
router.register(r"device-groups", views.DeviceGroupViewSet, basename="device-group")
# Issue #40 - Bulk Device Onboarding
router.register(r"bulk-onboarding", views.BulkOnboardingViewSet, basename="bulk-onboarding")
# Configuration Template Library (Issue #16)
router.register(r"config/templates", views.ConfigTemplateViewSet, basename="config-template")
# Configuration Drift Analysis
router.register(r"config/drift/alerts", views.DriftAlertViewSet, basename="drift-alert")
# NetBox Integration (Issue #9)
router.register(r"integrations/netbox", views.NetBoxConfigViewSet, basename="netbox-config")
# Email Notifications
router.register(r"notifications/smtp", SMTPConfigViewSet, basename="smtp-config")
router.register(
    r"notifications/preferences", NotificationPreferenceViewSet, basename="notification-preference"
)
router.register(r"notifications/events", NotificationEventViewSet, basename="notification-event")

urlpatterns = [
    path("auth/login", views.AuthViewSet.as_view({"post": "login"})),
    path("auth/refresh", views.AuthViewSet.as_view({"post": "refresh"})),
    path("auth/logout", views.AuthViewSet.as_view({"post": "logout"})),
    path("auth/me", views.AuthViewSet.as_view({"get": "me"})),
    path("commands/run", views.CommandViewSet.as_view({"post": "run"})),
    path("reachability/run", views.CommandViewSet.as_view({"post": "reachability"})),
    path("topology/discover", views.CommandViewSet.as_view({"post": "discover"})),
    path("config/backup", views.ConfigViewSet.as_view({"post": "backup"})),
    path("config/deploy/preview", views.ConfigViewSet.as_view({"post": "deploy_preview"})),
    path("config/deploy/commit", views.ConfigViewSet.as_view({"post": "deploy_commit"})),
    path("config/rollback/preview", views.ConfigViewSet.as_view({"post": "rollback_preview"})),
    path("config/rollback/commit", views.ConfigViewSet.as_view({"post": "rollback_commit"})),
    path("config/snapshots/<int:pk>", views.ConfigViewSet.as_view({"get": "snapshot"})),
    path(
        "config/devices/<int:device_id>/snapshots",
        views.ConfigViewSet.as_view({"get": "device_snapshots"}),
    ),
    path(
        "config/devices/<int:device_id>/diff",
        views.ConfigViewSet.as_view({"get": "diff"}),
    ),
    path("config/drift/detect", views.DriftViewSet.as_view({"post": "detect_drift"})),
    path("config/drift/analyze-device", views.DriftViewSet.as_view({"post": "analyze_device"})),
    path(
        "config/drift/device/<int:device_id>",
        views.DriftViewSet.as_view({"get": "device_drifts"}),
    ),
    path(
        "config/drift/device/<int:device_id>/frequency",
        views.DriftViewSet.as_view({"get": "change_frequency"}),
    ),
    path("config/drift/<int:pk>", views.DriftViewSet.as_view({"get": "detail"})),
    path("devices/import", views.DeviceImportView.as_view()),
    path("devices/<int:pk>/jobs", views.DeviceViewSet.as_view({"get": "jobs"})),
    path("devices/<int:pk>/snapshots", views.DeviceViewSet.as_view({"get": "snapshots"})),
    path("devices/<int:pk>/topology", views.DeviceViewSet.as_view({"get": "topology"})),
    path("jobs/<int:pk>/logs", views.JobLogsView.as_view()),
    path("jobs/<int:pk>/retry", views.JobViewSet.as_view({"post": "retry"})),
    path("jobs/<int:pk>/cancel", views.JobViewSet.as_view({"post": "cancel"})),
    path("", include(router.urls)),
]

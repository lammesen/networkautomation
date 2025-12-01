"""API URL wiring (initial skeleton)."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"customers", views.CustomerViewSet, basename="customer")
router.register(r"credentials", views.CredentialViewSet, basename="credential")
router.register(r"devices", views.DeviceViewSet, basename="device")
router.register(r"jobs", views.JobViewSet, basename="job")
router.register(r"jobs/admin", views.JobAdminViewSet, basename="job-admin")
router.register(r"compliance/policies", views.CompliancePolicyViewSet, basename="compliance-policy")
router.register(r"compliance/results", views.ComplianceResultViewSet, basename="compliance-result")
router.register(r"topology/links", views.TopologyLinkViewSet, basename="topology-link")

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
    path("devices/import", views.DeviceImportView.as_view()),
    path("devices/<int:pk>/jobs", views.DeviceViewSet.as_view({"get": "jobs"})),
    path("devices/<int:pk>/snapshots", views.DeviceViewSet.as_view({"get": "snapshots"})),
    path("devices/<int:pk>/topology", views.DeviceViewSet.as_view({"get": "topology"})),
    path("jobs/<int:pk>/logs", views.JobLogsView.as_view()),
    path("jobs/<int:pk>/retry", views.JobViewSet.as_view({"post": "retry"})),
    path("jobs/<int:pk>/cancel", views.JobViewSet.as_view({"post": "cancel"})),
    path("", include(router.urls)),
]

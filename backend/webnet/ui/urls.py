"""UI URL stubs for HTMX pages."""

from django.urls import path

from .views import (
    DashboardView,
    DeviceListView,
    DeviceDetailView,
    DeviceCreateView,
    DeviceImportView,
    DeviceSnapshotsPartialView,
    DeviceJobsPartialView,
    DeviceTopologyPartialView,
    JobListView,
    JobDetailView,
    JobDetailLogsView,
    ConfigSnapshotListView,
    ConfigDiffView,
    DriftTimelineView,
    DriftDetailView,
    DriftAlertsView,
    CompliancePolicyListView,
    ComplianceResultListView,
    ComplianceOverviewView,
    ComplianceRunView,
    RemediationRuleListView,
    RemediationActionListView,
    CommandsView,
    ReachabilityView,
    TopologyListView,
    WizardStep1View,
    WizardStep2View,
    WizardStep3View,
    WizardStep4View,
    GitSettingsListView,
    GitSettingsDetailView,
    GitSettingsCreateView,
    GitSettingsDeleteView,
    GitSyncView,
    GitTestConnectionView,
    GitSyncLogsView,
    # Issue #40 - Bulk Device Onboarding
    BulkOnboardingView,
    DiscoveryQueueView,
    DiscoveryQueueActionView,
    ScanIPRangeView,
    # Issue #24 - Device Tags and Groups
    TagListView,
    TagCreateView,
    TagDeleteView,
    DeviceGroupListView,
    DeviceGroupCreateView,
    DeviceGroupDetailView,
    DeviceGroupDeleteView,
    # Configuration Template Views (Issue #16)
    ConfigTemplateListView,
    ConfigTemplateDetailView,
    ConfigTemplateCreateView,
    ConfigTemplateDeleteView,
    ConfigTemplateRenderView,
    # NetBox Integration Views (Issue #9)
    NetBoxSettingsListView,
    NetBoxSettingsDetailView,
    NetBoxSettingsCreateView,
    NetBoxSettingsDeleteView,
    NetBoxSyncView,
    NetBoxTestConnectionView,
    NetBoxSyncLogsView,
    # SSH Host Key Management
    SSHHostKeyListView,
    SSHHostKeyVerifyView,
    SSHHostKeyDeleteView,
    SSHHostKeyImportView,
    # Webhook Integration
    WebhookListView,
    WebhookDeliveryListView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("devices/", DeviceListView.as_view(), name="devices-list"),
    path("devices/new", DeviceCreateView.as_view(), name="devices-create"),
    path("devices/import", DeviceImportView.as_view(), name="devices-import"),
    path("devices/<int:pk>/", DeviceDetailView.as_view(), name="devices-detail"),
    path(
        "devices/<int:pk>/snapshots", DeviceSnapshotsPartialView.as_view(), name="devices-snapshots"
    ),
    path("devices/<int:pk>/jobs", DeviceJobsPartialView.as_view(), name="devices-jobs"),
    path("devices/<int:pk>/topology", DeviceTopologyPartialView.as_view(), name="devices-topology"),
    path("jobs/", JobListView.as_view(), name="jobs-list"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="jobs-detail"),
    path("jobs/<int:pk>/logs", JobDetailLogsView.as_view(), name="jobs-logs"),
    path("config/", ConfigSnapshotListView.as_view(), name="config-list"),
    path("config/diff", ConfigDiffView.as_view(), name="config-diff"),
    path("config/drift/timeline", DriftTimelineView.as_view(), name="drift-timeline"),
    path("config/drift/<int:drift_id>/", DriftDetailView.as_view(), name="drift-detail"),
    path("config/drift/alerts", DriftAlertsView.as_view(), name="drift-alerts"),
    path("compliance/policies", CompliancePolicyListView.as_view(), name="compliance-policies"),
    path("compliance/results", ComplianceResultListView.as_view(), name="compliance-results"),
    path("compliance/overview", ComplianceOverviewView.as_view(), name="compliance-overview"),
    path("compliance/run", ComplianceRunView.as_view(), name="compliance-run"),
    path(
        "compliance/remediation-rules",
        RemediationRuleListView.as_view(),
        name="remediation-rules",
    ),
    path(
        "compliance/remediation-actions",
        RemediationActionListView.as_view(),
        name="remediation-actions",
    ),
    path("topology/", TopologyListView.as_view(), name="topology-list"),
    path("commands/", CommandsView.as_view(), name="commands-run"),
    path("commands/wizard/step1", WizardStep1View.as_view(), name="wizard-step1"),
    path("commands/wizard/step2", WizardStep2View.as_view(), name="wizard-step2"),
    path("commands/wizard/step3", WizardStep3View.as_view(), name="wizard-step3"),
    path("commands/wizard/step4", WizardStep4View.as_view(), name="wizard-step4"),
    path("reachability/", ReachabilityView.as_view(), name="reachability-run"),
    # Git integration settings
    path("settings/git/", GitSettingsListView.as_view(), name="git-settings"),
    path("settings/git/new", GitSettingsCreateView.as_view(), name="git-settings-create"),
    path("settings/git/<int:pk>/", GitSettingsDetailView.as_view(), name="git-settings-detail"),
    path(
        "settings/git/<int:pk>/delete", GitSettingsDeleteView.as_view(), name="git-settings-delete"
    ),
    path("settings/git/<int:pk>/sync", GitSyncView.as_view(), name="git-sync"),
    path("settings/git/<int:pk>/test", GitTestConnectionView.as_view(), name="git-test-connection"),
    path("settings/git/<int:pk>/logs", GitSyncLogsView.as_view(), name="git-sync-logs"),
    # Issue #40 - Bulk Device Onboarding
    path("devices/bulk-onboarding/", BulkOnboardingView.as_view(), name="bulk-onboarding"),
    path("devices/discovery-queue/", DiscoveryQueueView.as_view(), name="discovery-queue"),
    path(
        "devices/discovery/<int:pk>/<str:action>",
        DiscoveryQueueActionView.as_view(),
        name="discovery-action",
    ),
    path("devices/scan-ip-range/", ScanIPRangeView.as_view(), name="scan-ip-range"),
    # Issue #24 - Device Tags and Groups
    path("devices/tags/", TagListView.as_view(), name="tags-list"),
    path("devices/tags/new", TagCreateView.as_view(), name="tags-create"),
    path("devices/tags/<int:pk>/delete", TagDeleteView.as_view(), name="tags-delete"),
    path("devices/groups/", DeviceGroupListView.as_view(), name="groups-list"),
    path("devices/groups/new", DeviceGroupCreateView.as_view(), name="groups-create"),
    path("devices/groups/<int:pk>/", DeviceGroupDetailView.as_view(), name="groups-detail"),
    path("devices/groups/<int:pk>/delete", DeviceGroupDeleteView.as_view(), name="groups-delete"),
    # Configuration Template Library (Issue #16)
    path("templates/", ConfigTemplateListView.as_view(), name="templates-list"),
    path("templates/new", ConfigTemplateCreateView.as_view(), name="templates-create"),
    path("templates/<int:pk>/", ConfigTemplateDetailView.as_view(), name="templates-detail"),
    path("templates/<int:pk>/delete", ConfigTemplateDeleteView.as_view(), name="templates-delete"),
    path("templates/<int:pk>/render", ConfigTemplateRenderView.as_view(), name="templates-render"),
    # NetBox Integration (Issue #9)
    path("settings/netbox/", NetBoxSettingsListView.as_view(), name="netbox-settings"),
    path("settings/netbox/new", NetBoxSettingsCreateView.as_view(), name="netbox-settings-create"),
    path(
        "settings/netbox/<int:pk>/",
        NetBoxSettingsDetailView.as_view(),
        name="netbox-settings-detail",
    ),
    path(
        "settings/netbox/<int:pk>/delete",
        NetBoxSettingsDeleteView.as_view(),
        name="netbox-settings-delete",
    ),
    path("settings/netbox/<int:pk>/sync", NetBoxSyncView.as_view(), name="netbox-sync"),
    path(
        "settings/netbox/<int:pk>/test",
        NetBoxTestConnectionView.as_view(),
        name="netbox-test-connection",
    ),
    path("settings/netbox/<int:pk>/logs", NetBoxSyncLogsView.as_view(), name="netbox-sync-logs"),
    # SSH Host Key Management
    path("ssh/host-keys/", SSHHostKeyListView.as_view(), name="ssh-host-keys"),
    path(
        "ssh/host-keys/<int:pk>/verify/", SSHHostKeyVerifyView.as_view(), name="ssh-host-key-verify"
    ),
    path(
        "ssh/host-keys/<int:pk>/delete/", SSHHostKeyDeleteView.as_view(), name="ssh-host-key-delete"
    ),
    path("ssh/host-keys/import/", SSHHostKeyImportView.as_view(), name="ssh-host-key-import"),
    # Webhook Integration
    path("settings/webhooks/", WebhookListView.as_view(), name="webhooks-list"),
    path(
        "settings/webhooks/deliveries", WebhookDeliveryListView.as_view(), name="webhook-deliveries"
    ),
]

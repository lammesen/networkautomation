"""DRF serializers for webnet APIs."""

from rest_framework import serializers
from webnet.users.models import User, APIKey
from webnet.customers.models import Customer, CustomerIPRange
from webnet.devices.models import (
    Device,
    Credential,
    TopologyLink,
    DiscoveredDevice,
    SSHHostKey,
)
from webnet.devices.models import (
    NetBoxConfig,
    NetBoxSyncLog,
    ServiceNowConfig,
    ServiceNowSyncLog,
    ServiceNowIncident,
    ServiceNowChangeRequest,
)
from webnet.jobs.models import Job, JobLog
from webnet.config_mgmt.models import ConfigSnapshot, ConfigTemplate, ConfigDrift, DriftAlert
from webnet.compliance.models import (
    CompliancePolicy,
    ComplianceResult,
    RemediationRule,
    RemediationAction,
)
from webnet.ansible_mgmt.models import Playbook, AnsibleConfig


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_active", "customers", "date_joined"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "customers", "is_active"]


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "key_prefix",
            "scopes",
            "expires_at",
            "last_used_at",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["key_prefix", "created_at", "last_used_at"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "description", "ssh_host_key_policy", "created_at"]


class CustomerIPRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerIPRange
        fields = ["id", "customer", "cidr", "description", "created_at"]


class CredentialSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    enable_password = serializers.CharField(write_only=True, allow_null=True, required=False)

    class Meta:
        model = Credential
        fields = [
            "id",
            "customer",
            "name",
            "username",
            "password",
            "enable_password",
            "created_at",
        ]

    def create(self, validated_data):  # pragma: no cover - simple setter
        password = validated_data.pop("password")
        enable_password = validated_data.pop("enable_password", None)
        cred = Credential(**validated_data)
        cred.password = password
        if enable_password is not None:
            cred.enable_password = enable_password
        cred.save()
        return cred

    def update(self, instance, validated_data):  # pragma: no cover
        password = validated_data.pop("password", None)
        enable_password = validated_data.pop("enable_password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password is not None:
            instance.password = password
        if enable_password is not None:
            instance.enable_password = enable_password
        instance.save()
        return instance


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "id",
            "customer",
            "hostname",
            "mgmt_ip",
            "vendor",
            "platform",
            "role",
            "site",
            "tags",
            "credential",
            "enabled",
            "reachability_status",
            "last_reachability_check",
            "discovery_protocol",
            "created_at",
            "updated_at",
        ]


class DeviceImportSummarySerializer(serializers.Serializer):
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    skipped = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "customer",
            "type",
            "status",
            "user",
            "requested_at",
            "scheduled_for",
            "started_at",
            "finished_at",
            "target_summary_json",
            "result_summary_json",
            "payload_json",
        ]


class JobLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLog
        fields = ["id", "job", "ts", "level", "host", "message", "extra_json"]


class ConfigSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigSnapshot
        fields = ["id", "device", "job", "created_at", "source", "hash", "config_text"]
        read_only_fields = ["hash", "created_at"]


class ConfigDriftSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source="device.hostname", read_only=True)
    change_magnitude = serializers.CharField(source="get_change_magnitude", read_only=True)
    snapshot_from_created = serializers.DateTimeField(
        source="snapshot_from.created_at", read_only=True
    )
    snapshot_to_created = serializers.DateTimeField(source="snapshot_to.created_at", read_only=True)
    triggered_by_username = serializers.CharField(
        source="triggered_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = ConfigDrift
        fields = [
            "id",
            "device",
            "device_hostname",
            "snapshot_from",
            "snapshot_to",
            "snapshot_from_created",
            "snapshot_to_created",
            "detected_at",
            "additions",
            "deletions",
            "changes",
            "total_lines",
            "has_changes",
            "change_magnitude",
            "diff_summary",
            "triggered_by",
            "triggered_by_username",
        ]
        read_only_fields = ["detected_at", "change_magnitude"]


class DriftAlertSerializer(serializers.ModelSerializer):
    drift_device_hostname = serializers.CharField(source="drift.device.hostname", read_only=True)
    acknowledged_by_username = serializers.CharField(
        source="acknowledged_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = DriftAlert
        fields = [
            "id",
            "drift",
            "drift_device_hostname",
            "severity",
            "status",
            "message",
            "detected_at",
            "acknowledged_by",
            "acknowledged_by_username",
            "acknowledged_at",
            "resolution_notes",
        ]
        read_only_fields = ["detected_at"]


class CompliancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompliancePolicy
        fields = [
            "id",
            "customer",
            "name",
            "description",
            "scope_json",
            "definition_yaml",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ComplianceResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceResult
        fields = ["id", "policy", "device", "job", "ts", "status", "details_json"]
        read_only_fields = ["ts"]


class RemediationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationRule
        fields = [
            "id",
            "policy",
            "name",
            "description",
            "enabled",
            "config_snippet",
            "approval_required",
            "max_daily_executions",
            "apply_mode",
            "verify_after",
            "rollback_on_failure",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class RemediationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationAction
        fields = [
            "id",
            "rule",
            "compliance_result",
            "device",
            "job",
            "status",
            "before_snapshot",
            "after_snapshot",
            "verification_passed",
            "error_message",
            "started_at",
            "finished_at",
        ]
        # Note: read_only_fields specification is technically redundant since
        # RemediationActionViewSet is ReadOnlyModelViewSet, but kept for documentation
        # to clearly indicate which fields are system-managed
        read_only_fields = [
            "status",
            "before_snapshot",
            "after_snapshot",
            "verification_passed",
            "error_message",
            "started_at",
            "finished_at",
        ]


class TopologyLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopologyLink
        fields = [
            "id",
            "customer",
            "local_device",
            "local_interface",
            "remote_device",
            "remote_hostname",
            "remote_interface",
            "remote_ip",
            "remote_platform",
            "protocol",
            "discovered_at",
            "job_id",
        ]
        read_only_fields = ["discovered_at", "job_id"]


class SSHHostKeySerializer(serializers.ModelSerializer):
    """Serializer for SSH host keys."""

    device_hostname = serializers.CharField(source="device.hostname", read_only=True)
    verified_by_username = serializers.CharField(
        source="verified_by.username", read_only=True, allow_null=True
    )
    fingerprint_display = serializers.CharField(read_only=True)

    class Meta:
        model = SSHHostKey
        fields = [
            "id",
            "device",
            "device_hostname",
            "key_type",
            "public_key",
            "fingerprint_sha256",
            "fingerprint_display",
            "first_seen_at",
            "last_seen_at",
            "verified",
            "verified_by",
            "verified_by_username",
            "verified_at",
        ]
        read_only_fields = [
            "first_seen_at",
            "last_seen_at",
            "verified_by",
            "verified_at",
        ]


class SSHHostKeyVerifySerializer(serializers.Serializer):
    """Serializer for manually verifying/unverifying SSH host keys."""

    verified = serializers.BooleanField(required=True)


class SSHHostKeyImportSerializer(serializers.Serializer):
    """Serializer for importing SSH host keys from known_hosts format."""

    device_id = serializers.IntegerField(required=True)
    known_hosts_line = serializers.CharField(
        required=True,
        max_length=4096,
        trim_whitespace=True,
        help_text="OpenSSH known_hosts format line",
    )

    def validate_known_hosts_line(self, value):
        parts = value.strip().split()
        if len(parts) < 3:
            raise serializers.ValidationError(
                "Invalid format. Expected: hostname key_type key_data"
            )
        return value


class DiscoveredDeviceSerializer(serializers.ModelSerializer):
    """Serializer for discovered devices in the discovery queue.

    Provides read-only computed fields for related object display names.
    """

    discovered_via_device_hostname = serializers.CharField(
        source="discovered_via_device.hostname", read_only=True, allow_null=True
    )
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True, allow_null=True
    )
    created_device_hostname = serializers.CharField(
        source="created_device.hostname", read_only=True, allow_null=True
    )

    class Meta:
        model = DiscoveredDevice
        fields = [
            "id",
            "customer",
            "hostname",
            "mgmt_ip",
            "platform",
            "vendor",
            "serial_number",
            "software_version",
            "interfaces_json",
            "discovery_source",
            "discovered_via_device",
            "discovered_via_device_hostname",
            "discovered_via_protocol",
            "discovered_at",
            "last_seen_at",
            "job_id",
            "status",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "notes",
            "created_device",
            "created_device_hostname",
        ]
        read_only_fields = [
            "discovered_at",
            "last_seen_at",
            "job_id",
            "reviewed_at",
            "created_device",
        ]


class DiscoveredDeviceApproveSerializer(serializers.Serializer):
    """Serializer for approving a discovered device."""

    credential_id = serializers.IntegerField(help_text="ID of credential to assign")
    vendor = serializers.CharField(
        required=False, allow_blank=True, help_text="Device vendor (required if not auto-detected)"
    )
    platform = serializers.CharField(required=False, allow_blank=True, help_text="Device platform")
    role = serializers.CharField(required=False, allow_blank=True, help_text="Device role")
    site = serializers.CharField(required=False, allow_blank=True, help_text="Device site")


class DiscoveredDeviceRejectSerializer(serializers.Serializer):
    """Serializer for rejecting/ignoring a discovered device."""

    notes = serializers.CharField(required=False, allow_blank=True, help_text="Rejection reason")


class TopologyDiscoverRequestSerializer(serializers.Serializer):
    """Serializer for topology discovery request."""

    targets = serializers.DictField(required=False, default=dict, help_text="Device filter targets")
    protocol = serializers.ChoiceField(
        choices=["cdp", "lldp", "both"],
        default="both",
        help_text="Discovery protocol: 'cdp', 'lldp', or 'both'",
    )
    auto_create_devices = serializers.BooleanField(
        default=False, help_text="Automatically queue discovered unknown devices for review"
    )


# =============================================================================
# Bulk Device Onboarding Serializers (Issue #40)
# =============================================================================


class IPRangeScanRequestSerializer(serializers.Serializer):
    """Serializer for IP range scan request."""

    ip_ranges = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of IP ranges to scan (CIDR notation, e.g., '192.168.1.0/24')",
    )
    credential_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of credential IDs to try for each discovered device",
    )
    use_snmp = serializers.BooleanField(
        default=True, help_text="Use SNMP for device discovery and property detection"
    )
    snmp_community = serializers.CharField(
        required=False, allow_blank=True, default="public", help_text="SNMP community string"
    )
    snmp_version = serializers.ChoiceField(
        choices=["2c", "3"],
        default="2c",
        help_text="SNMP version to use",
    )
    test_ssh = serializers.BooleanField(
        default=True, help_text="Test SSH connectivity with provided credentials"
    )
    ports = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[22],
        help_text="Ports to scan for SSH connectivity",
    )


class CredentialTestRequestSerializer(serializers.Serializer):
    """Serializer for credential testing request."""

    ip_address = serializers.CharField(help_text="IP address to test credentials against")
    credential_id = serializers.IntegerField(help_text="Credential ID to test")
    port = serializers.IntegerField(default=22, help_text="SSH port")
    timeout = serializers.IntegerField(default=10, help_text="Connection timeout in seconds")


class CredentialTestResultSerializer(serializers.Serializer):
    """Serializer for credential test results."""

    success = serializers.BooleanField()
    credential_id = serializers.IntegerField()
    ip_address = serializers.CharField()
    message = serializers.CharField()
    device_info = serializers.DictField(required=False, allow_null=True)


class BulkDiscoveryResultSerializer(serializers.Serializer):
    """Serializer for bulk discovery results."""

    job_id = serializers.IntegerField()
    status = serializers.CharField()
    discovered_count = serializers.IntegerField()
    reachable_count = serializers.IntegerField()
    duplicate_count = serializers.IntegerField()


# =============================================================================
# Device Tags and Groups Serializers (Issue #24)
# =============================================================================


class TagSerializer(serializers.ModelSerializer):
    """Serializer for device tags."""

    device_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        from webnet.devices.models import Tag

        model = Tag
        fields = [
            "id",
            "customer",
            "name",
            "color",
            "description",
            "category",
            "created_at",
            "device_count",
        ]
        read_only_fields = ["created_at"]

    def validate_customer(self, value: Customer) -> Customer:
        """Validate that the user has access to the specified customer."""
        from webnet.api.permissions import user_has_customer_access

        request = self.context.get("request")
        if request and not user_has_customer_access(request.user, value.id):
            raise serializers.ValidationError("You do not have access to this customer.")
        return value


class DeviceGroupSerializer(serializers.ModelSerializer):
    """Serializer for device groups."""

    device_count = serializers.IntegerField(read_only=True, required=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="Device IDs for static membership",
    )

    class Meta:
        from webnet.devices.models import DeviceGroup

        model = DeviceGroup
        fields = [
            "id",
            "customer",
            "name",
            "description",
            "group_type",
            "filter_rules",
            "parent",
            "created_at",
            "updated_at",
            "device_count",
            "member_ids",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_customer(self, value: Customer) -> Customer:
        """Validate that the user has access to the specified customer."""
        from webnet.api.permissions import user_has_customer_access

        request = self.context.get("request")
        if request and not user_has_customer_access(request.user, value.id):
            raise serializers.ValidationError("You do not have access to this customer.")
        return value

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        instance = super().create(validated_data)
        if member_ids:
            devices = Device.objects.filter(id__in=member_ids, customer=instance.customer)
            instance.devices.set(devices)
        return instance

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        instance = super().update(instance, validated_data)
        if member_ids is not None:
            devices = Device.objects.filter(id__in=member_ids, customer=instance.customer)
            instance.devices.set(devices)
        return instance


class DeviceTagAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk tag assignment."""

    device_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Device IDs to assign tags to"
    )
    tag_ids = serializers.ListField(child=serializers.IntegerField(), help_text="Tag IDs to assign")
    action = serializers.ChoiceField(
        choices=["add", "remove", "set"],
        default="add",
        help_text="Action: 'add' tags, 'remove' tags, or 'set' (replace all)",
    )


class DeviceWithTagsSerializer(DeviceSerializer):
    """Extended device serializer with tag information."""

    device_tags = TagSerializer(source="device_tags_set", many=True, read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta(DeviceSerializer.Meta):
        fields = DeviceSerializer.Meta.fields + ["device_tags", "groups"]

    def get_groups(self, obj) -> list[dict]:
        """Get groups this device belongs to."""
        from webnet.devices.models import DeviceGroup

        groups = DeviceGroup.objects.filter(customer=obj.customer, devices=obj).values("id", "name")
        return list(groups)


class ConfigTemplateSerializer(serializers.ModelSerializer):
    """Serializer for configuration templates."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = ConfigTemplate
        fields = [
            "id",
            "customer",
            "name",
            "description",
            "category",
            "template_content",
            "variables_schema",
            "platform_tags",
            "is_active",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "created_by"]

    def validate_customer(self, value: Customer) -> Customer:
        """Validate that the user has access to the specified customer."""
        from webnet.api.permissions import user_has_customer_access

        request = self.context.get("request")
        if request and not user_has_customer_access(request.user, value.id):
            raise serializers.ValidationError("You do not have access to this customer.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class ConfigTemplateRenderSerializer(serializers.Serializer):
    """Serializer for rendering a configuration template."""

    variables = serializers.DictField(
        required=False, default=dict, help_text="Variable values for template rendering"
    )
    device_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="Optional device ID for context"
    )


class ConfigTemplateDeploySerializer(serializers.Serializer):
    """Serializer for deploying a rendered template to devices."""

    variables = serializers.DictField(
        required=False, default=dict, help_text="Variable values for template rendering"
    )
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of device IDs to deploy to",
    )
    mode = serializers.ChoiceField(
        choices=["merge", "replace"],
        default="merge",
        help_text="Deploy mode: merge or replace",
    )
    dry_run = serializers.BooleanField(
        default=True, help_text="If true, preview only without committing"
    )


# ==============================================================================
# NetBox Integration Serializers (Issue #9)
# ==============================================================================


class NetBoxConfigSerializer(serializers.ModelSerializer):
    """Serializer for NetBox configuration."""

    api_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True, help_text="NetBox API token"
    )
    has_api_token = serializers.SerializerMethodField()
    default_credential_name = serializers.CharField(
        source="default_credential.name", read_only=True, allow_null=True
    )

    class Meta:
        model = NetBoxConfig
        fields = [
            "id",
            "customer",
            "name",
            "api_url",
            "api_token",
            "has_api_token",
            "sync_frequency",
            "enabled",
            "site_filter",
            "tenant_filter",
            "role_filter",
            "status_filter",
            "field_mappings",
            "default_credential",
            "default_credential_name",
            "last_sync_at",
            "last_sync_status",
            "last_sync_message",
            "last_sync_stats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "last_sync_at",
            "last_sync_status",
            "last_sync_message",
            "last_sync_stats",
            "created_at",
            "updated_at",
        ]

    def get_has_api_token(self, obj) -> bool:
        return obj.has_api_token()

    def validate_customer(self, value: Customer) -> Customer:
        """Validate that the user has access to the specified customer."""
        from webnet.api.permissions import user_has_customer_access

        request = self.context.get("request")
        if request and not user_has_customer_access(request.user, value.id):
            raise serializers.ValidationError("You do not have access to this customer.")
        return value

    def validate(self, attrs):
        """Validate the serializer data."""
        # Require api_token on creation
        if self.instance is None:  # Create operation
            api_token = attrs.get("api_token")
            if not api_token:
                raise serializers.ValidationError(
                    {"api_token": "API token is required when creating a NetBox configuration."}
                )

        # Validate default_credential belongs to the same customer
        default_credential = attrs.get("default_credential")
        customer = attrs.get("customer") or (self.instance.customer if self.instance else None)

        if default_credential and customer:
            if default_credential.customer_id != customer.id:
                raise serializers.ValidationError(
                    {"default_credential": "Credential must belong to the same customer."}
                )

        return attrs

    def create(self, validated_data):
        api_token = validated_data.pop("api_token", None)
        instance = NetBoxConfig(**validated_data)
        if api_token:
            instance.api_token = api_token
        instance.save()
        return instance

    def update(self, instance, validated_data):
        api_token = validated_data.pop("api_token", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if api_token:
            instance.api_token = api_token
        instance.save()
        return instance


class NetBoxSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for NetBox sync logs."""

    class Meta:
        model = NetBoxSyncLog
        fields = [
            "id",
            "config",
            "status",
            "devices_created",
            "devices_updated",
            "devices_skipped",
            "devices_failed",
            "message",
            "details",
            "started_at",
            "finished_at",
        ]
        read_only_fields = [
            "status",
            "devices_created",
            "devices_updated",
            "devices_skipped",
            "devices_failed",
            "message",
            "details",
            "started_at",
            "finished_at",
        ]


class NetBoxSyncRequestSerializer(serializers.Serializer):
    """Serializer for triggering a NetBox sync."""

    full_sync = serializers.BooleanField(
        default=False, help_text="If true, sync all devices (not just delta)"
    )


class AnsibleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnsibleConfig
        fields = [
            "id",
            "customer",
            "ansible_cfg_content",
            "collections",
            "environment_vars",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PlaybookSerializer(serializers.ModelSerializer):
    uploaded_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Playbook
        fields = [
            "id",
            "customer",
            "name",
            "description",
            "source_type",
            "content",
            "git_repo_url",
            "git_branch",
            "git_path",
            "uploaded_file",
            "variables",
            "tags",
            "enabled",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate that required fields are provided based on source_type."""
        source_type = attrs.get("source_type", "inline")

        if source_type == "inline" and not attrs.get("content"):
            raise serializers.ValidationError(
                {"content": "Content is required for inline playbooks"}
            )
        elif source_type == "git":
            if not attrs.get("git_repo_url"):
                raise serializers.ValidationError(
                    {"git_repo_url": "Git repository URL is required for git source"}
                )
            if not attrs.get("git_path"):
                raise serializers.ValidationError(
                    {"git_path": "Git path is required for git source"}
                )
        elif source_type == "upload" and not attrs.get("uploaded_file"):
            # Only validate on create, not update
            if not self.instance:
                raise serializers.ValidationError(
                    {"uploaded_file": "File upload is required for upload source"}
                )

        return attrs

    def create(self, validated_data):
        # Set created_by to the current user
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class PlaybookExecuteSerializer(serializers.Serializer):
    """Serializer for executing a playbook."""

    targets = serializers.DictField(
        required=False,
        help_text="Device filter targets (site, role, vendor, device_ids)",
    )
    extra_vars = serializers.DictField(
        required=False,
        help_text="Extra variables to pass to the playbook",
    )
    limit = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Limit execution to specific hosts (Ansible limit pattern)",
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Ansible tags to run",
    )


# ==============================================================================
# ServiceNow Integration Serializers
# ==============================================================================


class ServiceNowConfigSerializer(serializers.ModelSerializer):
    """Serializer for ServiceNow configuration."""

    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, help_text="ServiceNow password"
    )
    has_password = serializers.SerializerMethodField()
    default_credential_name = serializers.CharField(
        source="default_credential.name", read_only=True, allow_null=True
    )

    class Meta:
        model = ServiceNowConfig
        fields = [
            "id",
            "customer",
            "name",
            "instance_url",
            "username",
            "password",
            "has_password",
            "cmdb_table",
            "ci_class",
            "ci_query_filter",
            "company_sys_id",
            "device_to_cmdb_mappings",
            "cmdb_to_device_mappings",
            "sync_frequency",
            "bidirectional_sync",
            "auto_sync_enabled",
            "default_credential",
            "default_credential_name",
            "create_incidents_on_failure",
            "incident_category",
            "incident_assignment_group",
            "create_changes_on_deploy",
            "change_category",
            "change_assignment_group",
            "last_sync_at",
            "last_sync_status",
            "last_sync_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "last_sync_at",
            "last_sync_status",
            "last_sync_message",
            "created_at",
            "updated_at",
        ]

    def get_has_password(self, obj) -> bool:
        return obj.has_password()

    def validate_customer(self, value: Customer) -> Customer:
        """Validate that the user has access to the specified customer."""
        from webnet.api.permissions import user_has_customer_access

        request = self.context.get("request")
        if request and not user_has_customer_access(request.user, value.id):
            raise serializers.ValidationError("You do not have access to this customer.")
        return value

    def validate(self, attrs):
        """Validate the serializer data."""
        # Require password on creation
        if self.instance is None:  # Create operation
            password = attrs.get("password")
            if not password:
                raise serializers.ValidationError(
                    {"password": "Password is required when creating a ServiceNow configuration."}
                )

        # Validate default_credential belongs to the same customer
        default_credential = attrs.get("default_credential")
        customer = attrs.get("customer") or (self.instance.customer if self.instance else None)

        if default_credential and customer:
            if default_credential.customer != customer:
                raise serializers.ValidationError(
                    {"default_credential": "Credential must belong to the same customer."}
                )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = ServiceNowConfig(**validated_data)
        if password:
            instance.password = password
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.password = password
        instance.save()
        return instance


class ServiceNowSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for ServiceNow sync logs."""

    class Meta:
        model = ServiceNowSyncLog
        fields = [
            "id",
            "config",
            "direction",
            "status",
            "devices_created",
            "devices_updated",
            "devices_skipped",
            "devices_failed",
            "message",
            "details",
            "started_at",
            "finished_at",
        ]
        read_only_fields = [
            "status",
            "devices_created",
            "devices_updated",
            "devices_skipped",
            "devices_failed",
            "message",
            "details",
            "started_at",
            "finished_at",
        ]


class ServiceNowSyncRequestSerializer(serializers.Serializer):
    """Serializer for triggering a ServiceNow sync."""

    direction = serializers.ChoiceField(
        choices=["import", "export", "both"],
        default="both",
        help_text="Sync direction: import (from ServiceNow), export (to ServiceNow), or both",
    )
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        help_text="Optional list of device IDs to sync (only for export)",
    )


class ServiceNowIncidentSerializer(serializers.ModelSerializer):
    """Serializer for ServiceNow incidents."""

    job_type = serializers.CharField(source="job.type", read_only=True)

    class Meta:
        model = ServiceNowIncident
        fields = [
            "id",
            "config",
            "job",
            "job_type",
            "incident_number",
            "incident_sys_id",
            "state",
            "short_description",
            "description",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "incident_number",
            "incident_sys_id",
            "created_at",
            "updated_at",
            "resolved_at",
        ]


class ServiceNowIncidentUpdateSerializer(serializers.Serializer):
    """Serializer for updating ServiceNow incidents."""

    state = serializers.ChoiceField(
        choices=[1, 2, 3, 6, 7],
        required=False,
        help_text="New incident state: 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed",
    )
    work_notes = serializers.CharField(
        required=False, allow_blank=True, help_text="Work notes to add to the incident"
    )
    resolution_notes = serializers.CharField(
        required=False, allow_blank=True, help_text="Resolution notes (when resolving)"
    )


class ServiceNowChangeRequestSerializer(serializers.ModelSerializer):
    """Serializer for ServiceNow change requests."""

    job_type = serializers.CharField(source="job.type", read_only=True)

    class Meta:
        model = ServiceNowChangeRequest
        fields = [
            "id",
            "config",
            "job",
            "job_type",
            "change_number",
            "change_sys_id",
            "state",
            "short_description",
            "description",
            "justification",
            "created_at",
            "updated_at",
            "closed_at",
        ]
        read_only_fields = [
            "change_number",
            "change_sys_id",
            "created_at",
            "updated_at",
            "closed_at",
        ]


class ServiceNowChangeRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating ServiceNow change requests."""

    short_description = serializers.CharField(
        max_length=255, help_text="Brief summary of the change"
    )
    description = serializers.CharField(help_text="Detailed description of the change")
    justification = serializers.CharField(help_text="Business justification for the change")
    risk = serializers.IntegerField(
        default=3, min_value=1, max_value=3, help_text="Risk level: 1=High, 2=Medium, 3=Low"
    )
    impact = serializers.IntegerField(
        default=3, min_value=1, max_value=3, help_text="Impact level: 1=High, 2=Medium, 3=Low"
    )
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        help_text="Optional list of device IDs affected by the change",
    )


class ServiceNowChangeRequestUpdateSerializer(serializers.Serializer):
    """Serializer for updating ServiceNow change requests."""

    state = serializers.ChoiceField(
        choices=[-5, 0, 1, 2, 3, 4, 6],
        required=False,
        help_text="New state: -5=New, 0=Assess, 1=Authorize, 2=Scheduled, 3=Implement, 4=Review, 6=Closed",
    )
    work_notes = serializers.CharField(
        required=False, allow_blank=True, help_text="Work notes to add to the change"
    )
    close_notes = serializers.CharField(
        required=False, allow_blank=True, help_text="Closing notes (when closing)"
    )

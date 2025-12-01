"""DRF serializers for webnet APIs."""

from rest_framework import serializers
from webnet.users.models import User, APIKey
from webnet.customers.models import Customer, CustomerIPRange
from webnet.devices.models import Device, Credential, TopologyLink, DiscoveredDevice
from webnet.devices.models import NetBoxConfig, NetBoxSyncLog
from webnet.jobs.models import Job, JobLog
from webnet.config_mgmt.models import ConfigSnapshot, ConfigTemplate
from webnet.compliance.models import CompliancePolicy, ComplianceResult


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
        fields = ["id", "name", "description", "created_at"]


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

"""DRF serializers (initial skeleton)."""

from rest_framework import serializers
from webnet.users.models import User, APIKey
from webnet.customers.models import Customer, CustomerIPRange
from webnet.devices.models import Device, Credential, TopologyLink, DiscoveredDevice
from webnet.jobs.models import Job, JobLog
from webnet.config_mgmt.models import ConfigSnapshot
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
    """Serializer for discovered devices in the discovery queue."""

    discovered_via_device_hostname = serializers.CharField(
        source="discovered_via_device.hostname", read_only=True
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

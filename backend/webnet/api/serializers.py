"""DRF serializers (initial skeleton)."""

from rest_framework import serializers
from webnet.users.models import User, APIKey
from webnet.customers.models import Customer, CustomerIPRange
from webnet.devices.models import Device, Credential, TopologyLink
from webnet.jobs.models import Job, JobLog
from webnet.config_mgmt.models import ConfigSnapshot, GitRepository, GitSyncLog
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


class GitRepositorySerializer(serializers.ModelSerializer):
    """Serializer for Git repository configuration.

    Write-only fields for sensitive auth credentials.
    """

    auth_token = serializers.CharField(
        write_only=True, allow_null=True, required=False, allow_blank=True
    )
    ssh_private_key = serializers.CharField(
        write_only=True, allow_null=True, required=False, allow_blank=True
    )
    has_auth_token = serializers.SerializerMethodField()
    has_ssh_key = serializers.SerializerMethodField()

    class Meta:
        model = GitRepository
        fields = [
            "id",
            "customer",
            "name",
            "remote_url",
            "branch",
            "auth_type",
            "auth_token",
            "ssh_private_key",
            "has_auth_token",
            "has_ssh_key",
            "path_structure",
            "enabled",
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

    def get_has_auth_token(self, obj: GitRepository) -> bool:
        """Check if auth token is configured (without exposing it)."""
        return bool(obj._auth_token)

    def get_has_ssh_key(self, obj: GitRepository) -> bool:
        """Check if SSH key is configured (without exposing it)."""
        return bool(obj._ssh_private_key)

    def create(self, validated_data: dict) -> GitRepository:
        auth_token = validated_data.pop("auth_token", None)
        ssh_private_key = validated_data.pop("ssh_private_key", None)

        repository = GitRepository(**validated_data)
        if auth_token:
            repository.auth_token = auth_token
        if ssh_private_key:
            repository.ssh_private_key = ssh_private_key
        repository.save()
        return repository

    def update(self, instance: GitRepository, validated_data: dict) -> GitRepository:
        auth_token = validated_data.pop("auth_token", None)
        ssh_private_key = validated_data.pop("ssh_private_key", None)

        for key, value in validated_data.items():
            setattr(instance, key, value)

        # Only update credentials if provided (allows partial updates)
        if auth_token:
            instance.auth_token = auth_token
        if ssh_private_key:
            instance.ssh_private_key = ssh_private_key

        instance.save()
        return instance


class GitSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for Git sync logs."""

    class Meta:
        model = GitSyncLog
        fields = [
            "id",
            "repository",
            "job",
            "status",
            "commit_hash",
            "files_synced",
            "message",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields  # All fields are read-only

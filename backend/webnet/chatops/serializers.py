"""ChatOps serializers."""

from __future__ import annotations

from rest_framework import serializers

from webnet.chatops.models import (
    SlackWorkspace,
    SlackChannel,
    SlackUserMapping,
    ChatOpsCommand,
)


class SlackWorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for SlackWorkspace."""

    class Meta:
        model = SlackWorkspace
        fields = [
            "id",
            "customer",
            "team_id",
            "team_name",
            "bot_user_id",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # Don't expose bot_token and signing_secret in serializer for security


class SlackWorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SlackWorkspace with sensitive fields."""

    class Meta:
        model = SlackWorkspace
        fields = [
            "id",
            "customer",
            "team_id",
            "team_name",
            "bot_token",
            "bot_user_id",
            "signing_secret",
            "enabled",
        ]
        read_only_fields = ["id"]


class SlackChannelSerializer(serializers.ModelSerializer):
    """Serializer for SlackChannel."""

    workspace_name = serializers.CharField(source="workspace.team_name", read_only=True)

    class Meta:
        model = SlackChannel
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "channel_id",
            "channel_name",
            "notify_job_completion",
            "notify_job_failure",
            "notify_compliance_violations",
            "notify_drift_detected",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace_name", "created_at", "updated_at"]


class SlackUserMappingSerializer(serializers.ModelSerializer):
    """Serializer for SlackUserMapping."""

    username = serializers.CharField(source="user.username", read_only=True)
    workspace_name = serializers.CharField(source="workspace.team_name", read_only=True)

    class Meta:
        model = SlackUserMapping
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "slack_user_id",
            "user",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace_name", "username", "created_at", "updated_at"]


class ChatOpsCommandSerializer(serializers.ModelSerializer):
    """Serializer for ChatOpsCommand."""

    username = serializers.CharField(source="user.username", read_only=True)
    workspace_name = serializers.CharField(source="workspace.team_name", read_only=True)

    class Meta:
        model = ChatOpsCommand
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "user",
            "username",
            "slack_user_id",
            "channel_id",
            "command",
            "response_status",
            "response_text",
            "job",
            "created_at",
        ]
        read_only_fields = ["id", "workspace_name", "username", "created_at"]

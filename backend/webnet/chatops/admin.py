"""Django admin configuration for ChatOps."""

from __future__ import annotations

from django.contrib import admin

from webnet.chatops.models import (
    SlackWorkspace,
    SlackChannel,
    SlackUserMapping,
    ChatOpsCommand,
)


@admin.register(SlackWorkspace)
class SlackWorkspaceAdmin(admin.ModelAdmin):
    """Admin interface for SlackWorkspace."""

    list_display = ["team_name", "team_id", "customer", "enabled", "created_at"]
    list_filter = ["enabled", "created_at"]
    search_fields = ["team_name", "team_id"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("customer", "team_id", "team_name", "bot_user_id", "enabled")}),
        (
            "Credentials",
            {
                "fields": ("bot_token", "signing_secret"),
                "classes": ("collapse",),
                "description": "Bot token and signing secret are sensitive. Handle with care.",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(SlackChannel)
class SlackChannelAdmin(admin.ModelAdmin):
    """Admin interface for SlackChannel."""

    list_display = [
        "channel_name",
        "workspace",
        "notify_job_completion",
        "notify_job_failure",
        "notify_compliance_violations",
        "notify_drift_detected",
    ]
    list_filter = [
        "workspace",
        "notify_job_completion",
        "notify_job_failure",
        "notify_compliance_violations",
        "notify_drift_detected",
    ]
    search_fields = ["channel_name", "channel_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SlackUserMapping)
class SlackUserMappingAdmin(admin.ModelAdmin):
    """Admin interface for SlackUserMapping."""

    list_display = ["slack_user_id", "user", "workspace", "created_at"]
    list_filter = ["workspace", "created_at"]
    search_fields = ["slack_user_id", "user__username"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ChatOpsCommand)
class ChatOpsCommandAdmin(admin.ModelAdmin):
    """Admin interface for ChatOpsCommand (read-only audit log)."""

    list_display = ["command", "user", "response_status", "workspace", "created_at"]
    list_filter = ["response_status", "workspace", "created_at"]
    search_fields = ["command", "user__username", "response_text"]
    readonly_fields = [
        "workspace",
        "user",
        "platform_user_id",
        "channel_id",
        "command",
        "response_status",
        "response_text",
        "job",
        "created_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        """Prevent manual creation of command logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of command logs."""
        return False

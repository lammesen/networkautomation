"""Microsoft Teams models for ChatOps integration."""

from __future__ import annotations

from django.db import models


class TeamsWorkspace(models.Model):
    """Microsoft Teams workspace/tenant configuration."""

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="teams_workspaces"
    )
    tenant_id = models.CharField(max_length=100, unique=True, help_text="Azure AD tenant ID")
    tenant_name = models.CharField(max_length=255, help_text="Tenant/organization name")
    bot_app_id = models.CharField(max_length=100, help_text="Bot application ID")
    bot_app_password = models.CharField(
        max_length=255, help_text="Bot application password (encrypted)"
    )
    service_url = models.CharField(
        max_length=500, help_text="Teams service URL", default="https://smba.trafficmanager.net/amer/"
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["tenant_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_name} ({self.tenant_id})"


class TeamsChannel(models.Model):
    """Microsoft Teams channel configuration for notifications."""

    workspace = models.ForeignKey(TeamsWorkspace, on_delete=models.CASCADE, related_name="channels")
    team_id = models.CharField(max_length=100, help_text="Teams team ID")
    channel_id = models.CharField(max_length=100, help_text="Teams channel ID")
    channel_name = models.CharField(max_length=255, help_text="Channel name")
    webhook_url = models.CharField(
        max_length=500, blank=True, help_text="Incoming webhook URL for notifications"
    )
    notify_job_completion = models.BooleanField(default=False)
    notify_job_failure = models.BooleanField(default=True)
    notify_compliance_violations = models.BooleanField(default=False)
    notify_drift_detected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["channel_id"]),
        ]
        unique_together = ["workspace", "channel_id"]

    def __str__(self) -> str:
        return f"{self.channel_name} ({self.workspace.tenant_name})"


class TeamsUserMapping(models.Model):
    """Map Teams users to Django users for authentication."""

    workspace = models.ForeignKey(
        TeamsWorkspace, on_delete=models.CASCADE, related_name="user_mappings"
    )
    teams_user_id = models.CharField(max_length=100, help_text="Teams user object ID (AAD)")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="teams_mappings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["teams_user_id"]),
        ]
        unique_together = ["workspace", "teams_user_id"]

    def __str__(self) -> str:
        return f"{self.teams_user_id} -> {self.user.username}"

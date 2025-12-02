"""ChatOps models for Slack/Teams integration."""

from __future__ import annotations

from django.db import models


class SlackWorkspace(models.Model):
    """Slack workspace configuration."""

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="slack_workspaces"
    )
    team_id = models.CharField(max_length=100, unique=True, help_text="Slack team ID")
    team_name = models.CharField(max_length=255, help_text="Slack team name")
    bot_token = models.CharField(max_length=255, help_text="Slack bot OAuth token (encrypted)")
    bot_user_id = models.CharField(max_length=100, help_text="Slack bot user ID")
    signing_secret = models.CharField(
        max_length=255, help_text="Slack signing secret for request verification"
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["team_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.team_name} ({self.team_id})"


class SlackChannel(models.Model):
    """Slack channel configuration for notifications."""

    workspace = models.ForeignKey(SlackWorkspace, on_delete=models.CASCADE, related_name="channels")
    channel_id = models.CharField(max_length=100, help_text="Slack channel ID")
    channel_name = models.CharField(max_length=255, help_text="Slack channel name")
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
        return f"{self.channel_name} ({self.workspace.team_name})"


class SlackUserMapping(models.Model):
    """Map Slack users to Django users for authentication."""

    workspace = models.ForeignKey(
        SlackWorkspace, on_delete=models.CASCADE, related_name="user_mappings"
    )
    slack_user_id = models.CharField(max_length=100, help_text="Slack user ID")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="slack_mappings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["slack_user_id"]),
        ]
        unique_together = ["workspace", "slack_user_id"]

    def __str__(self) -> str:
        return f"{self.slack_user_id} -> {self.user.username}"


class ChatOpsCommand(models.Model):
    """Audit log for ChatOps commands."""

    PLATFORM_CHOICES = [
        ("slack", "Slack"),
        ("teams", "Microsoft Teams"),
    ]

    workspace = models.ForeignKey(
        SlackWorkspace,
        on_delete=models.CASCADE,
        related_name="commands",
        null=True,
        blank=True,
        help_text="Slack workspace (if Slack command)",
    )
    teams_workspace = models.ForeignKey(
        "chatops.TeamsWorkspace",
        on_delete=models.CASCADE,
        related_name="commands",
        null=True,
        blank=True,
        help_text="Teams workspace (if Teams command)",
    )
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="slack", help_text="Platform used"
    )
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="chatops_commands"
    )
    platform_user_id = models.CharField(
        max_length=100, help_text="Platform-specific user ID (Slack or Teams)"
    )
    channel_id = models.CharField(max_length=100, help_text="Channel where command was issued")
    command = models.CharField(max_length=255, help_text="Command text")
    response_status = models.CharField(
        max_length=20,
        choices=[
            ("success", "Success"),
            ("error", "Error"),
            ("unauthorized", "Unauthorized"),
        ],
    )
    response_text = models.TextField(blank=True, help_text="Response sent to user")
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chatops_commands",
        help_text="Associated job if command created one",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["teams_workspace"]),
            models.Index(fields=["user"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.command} by {self.user.username} at {self.created_at}"


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
        max_length=500,
        help_text="Teams service URL",
        default="https://smba.trafficmanager.net/amer/",
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

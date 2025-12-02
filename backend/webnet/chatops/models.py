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

    workspace = models.ForeignKey(SlackWorkspace, on_delete=models.CASCADE, related_name="commands")
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="chatops_commands"
    )
    slack_user_id = models.CharField(max_length=100, help_text="Slack user ID")
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
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.command} by {self.user.username} at {self.created_at}"

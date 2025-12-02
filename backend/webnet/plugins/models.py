"""Models for plugin management."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from webnet.customers.models import Customer


class PluginConfig(models.Model):
    """Configuration and state for an installed plugin."""

    name = models.CharField(max_length=255, unique=True, help_text="Unique plugin identifier")
    verbose_name = models.CharField(max_length=255, help_text="Human-readable plugin name")
    description = models.TextField(blank=True, help_text="Plugin description")
    version = models.CharField(max_length=50, help_text="Plugin version")
    author = models.CharField(max_length=255, blank=True, help_text="Plugin author")

    # Plugin state
    enabled = models.BooleanField(default=True, help_text="Whether plugin is globally enabled")
    installed_at = models.DateTimeField(default=timezone.now, help_text="Installation timestamp")

    # Plugin configuration as JSON
    settings = models.JSONField(default=dict, blank=True, help_text="Plugin-specific settings")

    # Metadata
    min_webnet_version = models.CharField(
        max_length=50, blank=True, help_text="Minimum compatible webnet version"
    )
    max_webnet_version = models.CharField(
        max_length=50, blank=True, help_text="Maximum compatible webnet version"
    )
    dependencies = models.JSONField(
        default=list, blank=True, help_text="List of required plugin dependencies"
    )

    class Meta:
        ordering = ["verbose_name"]
        verbose_name = "Plugin Configuration"
        verbose_name_plural = "Plugin Configurations"

    def __str__(self) -> str:
        return f"{self.verbose_name} ({self.version})"


class CustomerPluginConfig(models.Model):
    """Per-customer plugin enablement and configuration."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="plugin_configs")
    plugin = models.ForeignKey(
        PluginConfig, on_delete=models.CASCADE, related_name="customer_configs"
    )

    enabled = models.BooleanField(
        default=True, help_text="Whether plugin is enabled for this customer"
    )
    settings = models.JSONField(
        default=dict, blank=True, help_text="Customer-specific plugin settings"
    )

    enabled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("customer", "plugin")]
        ordering = ["customer", "plugin"]
        verbose_name = "Customer Plugin Configuration"
        verbose_name_plural = "Customer Plugin Configurations"

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"{self.plugin.verbose_name} for {self.customer.name} ({status})"


class PluginAuditLog(models.Model):
    """Audit log for plugin operations."""

    ACTION_CHOICES = [
        ("install", "Install"),
        ("uninstall", "Uninstall"),
        ("enable", "Enable"),
        ("disable", "Disable"),
        ("configure", "Configure"),
        ("error", "Error"),
    ]

    plugin = models.ForeignKey(PluginConfig, on_delete=models.CASCADE, related_name="audit_logs")
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="plugin_audit_logs",
        null=True,
        blank=True,
        help_text="Customer context if applicable",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action",
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.JSONField(default=dict, blank=True, help_text="Action details and metadata")
    success = models.BooleanField(default=True, help_text="Whether action succeeded")
    error_message = models.TextField(blank=True, help_text="Error message if failed")

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Plugin Audit Log"
        verbose_name_plural = "Plugin Audit Logs"
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["plugin", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} - {self.plugin.name} at {self.timestamp}"

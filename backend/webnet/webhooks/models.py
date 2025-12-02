"""Webhook models for event notifications to external systems."""

from django.db import models
from webnet.core.crypto import encrypt_text, decrypt_text


class Webhook(models.Model):
    """Webhook configuration for sending event notifications to external systems.

    Webhooks enable integration with monitoring systems, ChatOps platforms,
    and downstream automation workflows by delivering real-time notifications
    when events occur in webnet.
    """

    EVENT_TYPE_CHOICES = [
        # Job events
        ("job.created", "Job Created"),
        ("job.started", "Job Started"),
        ("job.completed", "Job Completed"),
        ("job.failed", "Job Failed"),
        # Device events
        ("device.created", "Device Created"),
        ("device.updated", "Device Updated"),
        ("device.deleted", "Device Deleted"),
        ("device.status_changed", "Device Status Changed"),
        # Config events
        ("config.backup_created", "Config Backup Created"),
        ("config.changed", "Config Changed"),
        ("config.deployed", "Config Deployed"),
        # Compliance events
        ("compliance.check_completed", "Compliance Check Completed"),
        ("compliance.violation_detected", "Compliance Violation Detected"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="webhooks",
        help_text="Customer this webhook belongs to",
    )
    name = models.CharField(
        max_length=100,
        help_text="Friendly name for this webhook",
    )
    url = models.URLField(
        max_length=500,
        help_text="Destination URL for webhook POST requests",
    )
    event_types = models.JSONField(
        default=list,
        help_text="List of event types this webhook subscribes to",
    )
    _secret = models.TextField(
        db_column="secret",
        blank=True,
        null=True,
        help_text="Encrypted secret token for HMAC signature verification",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this webhook is active",
    )
    verify_ssl = models.BooleanField(
        default=True,
        help_text="Whether to verify SSL certificates for HTTPS URLs",
    )
    timeout_seconds = models.IntegerField(
        default=10,
        help_text="Request timeout in seconds",
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum number of retry attempts for failed deliveries",
    )
    retry_backoff = models.IntegerField(
        default=60,
        help_text="Initial retry backoff in seconds (doubles each retry)",
    )
    headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional HTTP headers to send with webhook requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_webhooks",
    )

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.customer.name})"

    @property
    def secret(self) -> str | None:
        """Decrypt and return the secret token."""
        if not self._secret:
            return None
        return decrypt_text(self._secret)

    @secret.setter
    def secret(self, value: str | None) -> None:
        """Encrypt and store the secret token."""
        if value:
            self._secret = encrypt_text(value)
        else:
            self._secret = ""

    def has_secret(self) -> bool:
        """Check if a secret token is configured."""
        return bool(self._secret)

    def subscribes_to(self, event_type: str) -> bool:
        """Check if this webhook subscribes to a specific event type."""
        return event_type in self.event_types


class WebhookDelivery(models.Model):
    """Log of webhook delivery attempts.

    Tracks the status and details of each webhook delivery for audit
    and debugging purposes.
    """

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_RETRYING = "retrying"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_RETRYING, "Retrying"),
    ]

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
        help_text="Webhook configuration used for this delivery",
    )
    event_type = models.CharField(
        max_length=50,
        help_text="Type of event that triggered this delivery",
    )
    event_id = models.IntegerField(
        help_text="ID of the entity that triggered the event",
    )
    payload = models.JSONField(
        help_text="JSON payload sent to the webhook URL",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    attempts = models.IntegerField(
        default=0,
        help_text="Number of delivery attempts",
    )
    http_status = models.IntegerField(
        null=True,
        blank=True,
        help_text="HTTP status code from last attempt",
    )
    response_body = models.TextField(
        blank=True,
        null=True,
        help_text="Response body from last attempt (truncated to 10KB)",
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message from last failed attempt",
    )
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Request duration in milliseconds",
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled time for next retry attempt",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook"]),
            models.Index(fields=["status"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Delivery {self.id} for {self.webhook.name} - {self.status}"

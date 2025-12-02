from django.db import models


class SMTPConfig(models.Model):
    """SMTP server configuration for sending email notifications."""

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="smtp_config",
    )
    host = models.CharField(max_length=255, help_text="SMTP server hostname")
    port = models.IntegerField(default=587, help_text="SMTP server port")
    use_tls = models.BooleanField(default=True, help_text="Use TLS encryption")
    use_ssl = models.BooleanField(default=False, help_text="Use SSL encryption")
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    from_email = models.EmailField(help_text="From address for sent emails")
    reply_to_email = models.EmailField(blank=True, null=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SMTP Configuration"
        verbose_name_plural = "SMTP Configurations"

    def __str__(self) -> str:  # pragma: no cover
        return f"SMTP Config for {self.customer.name}"


class NotificationPreference(models.Model):
    """User preferences for email notifications."""

    EVENT_CHOICES = (
        ("job_success", "Job Completed (Success)"),
        ("job_failed", "Job Failed"),
        ("job_partial", "Job Partial Success"),
        ("compliance_violation", "Compliance Violation Detected"),
        ("scheduled_backup_complete", "Scheduled Backup Completed"),
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    enabled = models.BooleanField(default=True)
    email_address = models.EmailField(
        blank=True,
        null=True,
        help_text="Override email (leave blank to use user's email)",
    )
    # Additional notification filters
    job_types = models.JSONField(
        blank=True,
        null=True,
        help_text="Filter by job types (null = all types)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "customer", "event_type")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user.username} - {self.event_type}"


class NotificationEvent(models.Model):
    """Log of notification events sent."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notification_events",
    )
    recipient_email = models.EmailField()
    event_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)
    # Link to related objects
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="notification_events",
        blank=True,
        null=True,
    )
    compliance_result = models.ForeignKey(
        "compliance.ComplianceResult",
        on_delete=models.CASCADE,
        related_name="notification_events",
        blank=True,
        null=True,
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.event_type} to {self.recipient_email} - {self.status}"

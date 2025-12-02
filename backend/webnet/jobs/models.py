from django.db import models
from webnet.core.custom_fields import CustomFieldMixin


class Schedule(models.Model):
    """Recurring job schedule with cron-like expressions."""

    INTERVAL_CHOICES = (
        ("cron", "CRON Expression"),
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    )

    # Import TYPE_CHOICES from Job to maintain consistency
    # We'll define it after Job class, but for now use CharField without choices
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="schedules"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    job_type = models.CharField(max_length=50)  # Will use Job.TYPE_CHOICES
    enabled = models.BooleanField(default=True)
    interval_type = models.CharField(max_length=20, choices=INTERVAL_CHOICES, default="daily")
    cron_expression = models.CharField(
        max_length=255, blank=True, help_text="Cron expression (e.g., '0 2 * * *')"
    )
    target_summary_json = models.JSONField(blank=True, null=True)
    payload_json = models.JSONField(blank=True, null=True)
    next_run = models.DateTimeField(blank=True, null=True)
    last_run = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="created_schedules"
    )

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["enabled"]),
            models.Index(fields=["next_run"]),
        ]
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.get_interval_type_display()})"

    def get_job_type_display(self) -> str:
        """Get display name for job type."""
        for value, label in Job.TYPE_CHOICES:
            if value == self.job_type:
                return label
        return self.job_type


class Job(CustomFieldMixin, models.Model):
    TYPE_CHOICES = (
        ("run_commands", "Run commands"),
        ("config_backup", "Config backup"),
        ("config_deploy_preview", "Config deploy preview"),
        ("config_deploy_commit", "Config deploy commit"),
        ("compliance_check", "Compliance check"),
        ("topology_discovery", "Topology discovery"),
        ("ansible_playbook", "Ansible playbook"),
    )
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("scheduled", "Scheduled"),
        ("running", "Running"),
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="jobs"
    )
    schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL, related_name="jobs", blank=True, null=True
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="jobs")
    region = models.ForeignKey(
        "core.Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        help_text="Region where this job is/was executed",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    target_summary_json = models.JSONField(blank=True, null=True)
    result_summary_json = models.JSONField(blank=True, null=True)
    payload_json = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
            models.Index(fields=["user"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["region"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Job {self.id} ({self.type})"


class JobLog(models.Model):
    LEVEL_CHOICES = (
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("WARN", "WARN"),
        ("ERROR", "ERROR"),
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="logs")
    ts = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    host = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    extra_json = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["job", "ts"]),
        ]
        ordering = ["ts"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Log {self.id} for job {self.job_id}"

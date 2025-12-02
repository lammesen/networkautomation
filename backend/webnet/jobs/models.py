from django.db import models


class Job(models.Model):
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
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="jobs")
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

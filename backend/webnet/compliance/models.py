from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class CompliancePolicy(models.Model):
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="compliance_policies"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    scope_json = models.JSONField()
    definition_yaml = models.TextField()
    created_by = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="created_policies"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ComplianceResult(models.Model):
    policy = models.ForeignKey(CompliancePolicy, on_delete=models.CASCADE, related_name="results")
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="compliance_results"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="compliance_results")
    ts = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    details_json = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["policy"]),
            models.Index(fields=["device"]),
            models.Index(fields=["ts"]),
        ]
        ordering = ["-ts"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Result {self.id} for policy {self.policy_id}"


class RemediationRule(models.Model):
    """Auto-remediation rule for compliance policy violations.

    Defines a configuration snippet that can be automatically applied
    when a compliance policy violation is detected.
    """

    APPROVAL_CHOICES = [
        ("none", "No Approval Required"),
        ("manual", "Manual Approval Required"),
        ("auto", "Auto-approve for Non-critical"),
    ]

    policy = models.ForeignKey(
        CompliancePolicy, on_delete=models.CASCADE, related_name="remediation_rules"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    enabled = models.BooleanField(default=True)
    config_snippet = models.TextField(help_text="Configuration commands to apply as remediation")
    approval_required = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default="manual")
    max_daily_executions = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Maximum number of remediations per day to prevent runaway fixes",
    )
    apply_mode = models.CharField(
        max_length=20,
        choices=[("merge", "Merge"), ("replace", "Replace")],
        default="merge",
        help_text="How to apply the configuration",
    )
    verify_after = models.BooleanField(
        default=True, help_text="Re-run compliance check after applying remediation"
    )
    rollback_on_failure = models.BooleanField(
        default=True, help_text="Rollback changes if remediation fails"
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="remediation_rules"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["policy", "name"]
        indexes = [
            models.Index(fields=["policy"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} for {self.policy.name}"


class RemediationAction(models.Model):
    """Audit log of auto-remediation executions.

    Records every auto-remediation attempt including before/after snapshots,
    success/failure status, and any error messages.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("rolled_back", "Rolled Back"),
    ]

    rule = models.ForeignKey(RemediationRule, on_delete=models.CASCADE, related_name="actions")
    compliance_result = models.ForeignKey(
        ComplianceResult,
        on_delete=models.CASCADE,
        related_name="remediation_actions",
        help_text="The compliance violation that triggered this remediation",
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="remediation_actions"
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remediation_actions",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    before_snapshot = models.ForeignKey(
        "config_mgmt.ConfigSnapshot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remediation_before",
        help_text="Configuration snapshot before remediation",
    )
    after_snapshot = models.ForeignKey(
        "config_mgmt.ConfigSnapshot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remediation_after",
        help_text="Configuration snapshot after remediation",
    )
    verification_passed = models.BooleanField(
        null=True, blank=True, help_text="Did the compliance check pass after remediation"
    )
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["rule"]),
            models.Index(fields=["device"]),
            models.Index(fields=["status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Remediation {self.id} - {self.rule.name} on {self.device.hostname}"

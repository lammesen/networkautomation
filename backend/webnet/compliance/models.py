from django.db import models


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

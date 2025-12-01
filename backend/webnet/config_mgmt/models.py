import hashlib
from django.db import models


class ConfigSnapshot(models.Model):
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="config_snapshots"
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        related_name="config_snapshots",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, default="manual")
    config_text = models.TextField()
    hash = models.CharField(max_length=64, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["device"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Snapshot {self.id} for device {self.device_id}"

    def save(self, *args, **kwargs):  # pragma: no cover - deterministic hashing
        if self.config_text and not self.hash:
            self.hash = hashlib.sha256(self.config_text.encode()).hexdigest()
        super().save(*args, **kwargs)

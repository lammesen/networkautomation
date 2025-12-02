"""Core models for webnet infrastructure."""

from django.db import models
from django.utils import timezone


class Region(models.Model):
    """Region for multi-region deployment support.

    Represents a geographic or logical region where workers can be deployed
    to reduce latency and improve reliability for network automation tasks.
    """

    STATUS_HEALTHY = "healthy"
    STATUS_DEGRADED = "degraded"
    STATUS_OFFLINE = "offline"

    STATUS_CHOICES = [
        (STATUS_HEALTHY, "Healthy"),
        (STATUS_DEGRADED, "Degraded"),
        (STATUS_OFFLINE, "Offline"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="regions",
        help_text="Customer this region belongs to",
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for the region (e.g., 'US East', 'Europe West')",
    )
    identifier = models.SlugField(
        max_length=50,
        help_text="Unique identifier for routing (e.g., 'us-east-1', 'eu-west-1')",
    )
    api_endpoint = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional API endpoint URL for this region (for distributed API)",
    )
    worker_pool_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuration for Celery worker pool (concurrency, queues, etc.)",
    )
    health_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_HEALTHY,
        help_text="Current health status of the region",
    )
    last_health_check = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last health check",
    )
    health_check_interval_seconds = models.IntegerField(
        default=60,
        help_text="Interval in seconds between health checks",
    )
    priority = models.IntegerField(
        default=100,
        help_text="Priority for job routing (higher = preferred). Used for failover.",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this region is enabled for job routing",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the region",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "identifier")
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["identifier"]),
            models.Index(fields=["health_status"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.identifier})"

    @property
    def queue_name(self) -> str:
        """Return the Celery queue name for this region."""
        return f"region_{self.identifier}"

    def is_available(self) -> bool:
        """Check if region is available for job routing."""
        return self.enabled and self.health_status != self.STATUS_OFFLINE

    def update_health_status(self, status: str, message: str | None = None) -> None:
        """Update the health status of this region.

        Args:
            status: New health status (healthy, degraded, offline)
            message: Optional message describing the health status
        """
        self.health_status = status
        self.last_health_check = timezone.now()
        if message and self.worker_pool_config:
            self.worker_pool_config["last_health_message"] = message
        self.save(update_fields=["health_status", "last_health_check", "worker_pool_config"])


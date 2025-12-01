from django.db import models


class Customer(models.Model):
    SSH_POLICY_STRICT = "strict"
    SSH_POLICY_TOFU = "tofu"
    SSH_POLICY_DISABLED = "disabled"

    SSH_POLICY_CHOICES = [
        (SSH_POLICY_STRICT, "Strict - Reject unknown/changed keys"),
        (SSH_POLICY_TOFU, "TOFU - Accept first, warn on change"),
        (SSH_POLICY_DISABLED, "Disabled - No verification (not recommended)"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    ssh_host_key_policy = models.CharField(
        max_length=20,
        choices=SSH_POLICY_CHOICES,
        default=SSH_POLICY_TOFU,
        help_text="SSH host key verification policy for this customer",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class CustomerIPRange(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="ip_ranges")
    cidr = models.CharField(max_length=45)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["customer"])]
        verbose_name = "Customer IP range"
        verbose_name_plural = "Customer IP ranges"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer_id}:{self.cidr}"

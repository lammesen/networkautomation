from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("viewer", "Viewer"),
        ("operator", "Operator"),
        ("admin", "Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    customers = models.ManyToManyField(
        "customers.Customer",
        related_name="users",
        blank=True,
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.username


class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=8)
    key_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["key_hash"]),
        ]
        verbose_name = "API key"
        verbose_name_plural = "API keys"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id}:{self.name}"

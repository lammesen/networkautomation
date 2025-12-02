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

    # 2FA fields
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_required = models.BooleanField(
        default=False, help_text="If True, user must enable 2FA before accessing the system"
    )
    backup_codes = models.JSONField(
        default=list, blank=True, help_text="Hashed backup codes for account recovery"
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.username

    def has_backup_codes(self) -> bool:
        """Check if user has any unused backup codes."""
        return bool(self.backup_codes)

    def is_2fa_enabled(self) -> bool:
        """Check if 2FA is enabled for this user."""
        return self.two_factor_enabled


class WebAuthnCredential(models.Model):
    """WebAuthn/FIDO2 security key credential."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webauthn_credentials")
    name = models.CharField(max_length=100, help_text="User-friendly name for this security key")
    credential_id = models.BinaryField(unique=True, help_text="WebAuthn credential ID")
    public_key = models.BinaryField(help_text="Public key for this credential")
    sign_count = models.PositiveIntegerField(default=0, help_text="Signature counter")
    aaguid = models.BinaryField(help_text="Authenticator AAGUID")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["credential_id"]),
        ]
        verbose_name = "WebAuthn Credential"
        verbose_name_plural = "WebAuthn Credentials"

    def __str__(self) -> str:
        return f"{self.user.username}: {self.name}"


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

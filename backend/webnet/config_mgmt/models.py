import hashlib
from django.db import models

from webnet.core.crypto import encrypt_text, decrypt_text


class GitRepository(models.Model):
    """Git repository configuration for exporting config snapshots.

    Each customer can configure a single Git repository to automatically
    push configuration backups after backup jobs complete.
    """

    AUTH_TYPE_CHOICES = [
        ("token", "Access Token (HTTPS)"),
        ("ssh_key", "SSH Key"),
    ]

    PATH_STRUCTURE_CHOICES = [
        ("by_customer", "By Customer: /{customer}/{device}/config.txt"),
        ("by_site", "By Site: /{site}/{device}/config.txt"),
        ("flat", "Flat: /{device}.txt"),
    ]

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="git_repository",
        help_text="Customer this repository belongs to",
    )
    name = models.CharField(
        max_length=100,
        help_text="Friendly name for this repository configuration",
    )
    remote_url = models.CharField(
        max_length=500,
        help_text="Git remote URL (HTTPS or SSH format)",
    )
    branch = models.CharField(
        max_length=100,
        default="main",
        help_text="Branch to push configs to",
    )
    auth_type = models.CharField(
        max_length=20,
        choices=AUTH_TYPE_CHOICES,
        default="token",
        help_text="Authentication method",
    )
    _auth_token = models.TextField(
        db_column="auth_token",
        blank=True,
        null=True,
        help_text="Encrypted access token for HTTPS authentication",
    )
    _ssh_private_key = models.TextField(
        db_column="ssh_private_key",
        blank=True,
        null=True,
        help_text="Encrypted SSH private key for SSH authentication",
    )
    path_structure = models.CharField(
        max_length=20,
        choices=PATH_STRUCTURE_CHOICES,
        default="by_customer",
        help_text="Directory structure for config files in the repository",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether auto-push is enabled after backups",
    )
    last_sync_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last successful sync timestamp",
    )
    last_sync_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Status of last sync attempt",
    )
    last_sync_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message or error from last sync attempt",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Git Repository"
        verbose_name_plural = "Git Repositories"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer.name} - {self.name}"

    @property
    def auth_token(self) -> str | None:
        """Decrypt and return the auth token."""
        return decrypt_text(self._auth_token)

    @auth_token.setter
    def auth_token(self, value: str | None) -> None:
        """Encrypt and store the auth token."""
        self._auth_token = encrypt_text(value) if value else ""

    @property
    def ssh_private_key(self) -> str | None:
        """Decrypt and return the SSH private key."""
        return decrypt_text(self._ssh_private_key)

    @ssh_private_key.setter
    def ssh_private_key(self, value: str | None) -> None:
        """Encrypt and store the SSH private key."""
        self._ssh_private_key = encrypt_text(value) if value else ""

    def has_auth_token(self) -> bool:
        """Check if an auth token is configured (for templates)."""
        return bool(self._auth_token)

    def has_ssh_key(self) -> bool:
        """Check if an SSH key is configured (for templates)."""
        return bool(self._ssh_private_key)

    def get_config_path(self, device, customer_name: str | None = None) -> str:
        """Generate the file path for a device's config based on path_structure.

        Args:
            device: The device whose config is being saved (Device instance)
            customer_name: Optional customer name (defaults to device.customer.name)

        Returns:
            Relative path within the repository for this device's config
        """
        hostname = device.hostname.replace("/", "_").replace("\\", "_")

        if self.path_structure == "by_customer":
            customer = customer_name or device.customer.name
            customer = customer.replace("/", "_").replace("\\", "_")
            return f"{customer}/{hostname}/config.txt"
        elif self.path_structure == "by_site":
            site = (device.site or "unknown").replace("/", "_").replace("\\", "_")
            return f"{site}/{hostname}/config.txt"
        else:  # flat
            return f"{hostname}.txt"


class GitSyncLog(models.Model):
    """Log of Git sync operations for audit trail."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    repository = models.ForeignKey(
        GitRepository,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        related_name="git_sync_logs",
        null=True,
        blank=True,
        help_text="Associated backup job that triggered this sync",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    commit_hash = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Git commit SHA if sync was successful",
    )
    files_synced = models.IntegerField(
        default=0,
        help_text="Number of config files pushed in this sync",
    )
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Commit message or error details",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["repository"]),
            models.Index(fields=["status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Sync {self.id} for {self.repository_id} - {self.status}"


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
    # Git sync tracking
    git_synced = models.BooleanField(
        default=False,
        help_text="Whether this snapshot has been synced to Git",
    )
    git_commit_hash = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Git commit SHA this snapshot was synced in",
    )
    git_sync_log = models.ForeignKey(
        GitSyncLog,
        on_delete=models.SET_NULL,
        related_name="snapshots",
        null=True,
        blank=True,
    )

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

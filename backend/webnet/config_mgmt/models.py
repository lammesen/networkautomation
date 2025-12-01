import hashlib
import ipaddress as ip_module
import json
from typing import Any

from django.db import models
from django.core.validators import MinLengthValidator

from webnet.core.crypto import encrypt_text, decrypt_text


class ConfigTemplate(models.Model):
    """Jinja2 configuration template for device configs.

    Templates can define variables with types and validation rules,
    enabling standardized configuration generation with previews.
    """

    CATEGORY_CHOICES = [
        ("base", "Base Config (hostname, logging, NTP)"),
        ("interface", "Interface Templates"),
        ("routing", "Routing Protocols"),
        ("security", "Security Policies"),
        ("custom", "Custom Templates"),
    ]

    VARIABLE_TYPES = [
        ("string", "String"),
        ("integer", "Integer"),
        ("ipaddress", "IP Address"),
        ("list", "List"),
        ("boolean", "Boolean"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="config_templates",
        help_text="Customer this template belongs to",
    )
    name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(1)],
        help_text="Template name",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Template description and usage notes",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="custom",
        help_text="Template category for organization",
    )
    template_content = models.TextField(
        help_text="Jinja2 template content",
    )
    variables_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Variable definitions: {name: {type, required, default, description, validation}}"
        ),
    )
    platform_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of compatible platform/vendor tags (e.g., ['cisco_ios', 'juniper'])",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for use",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.category})"

    def get_variables(self) -> dict[str, dict[str, Any]]:
        """Return the variables schema as a dictionary."""
        if isinstance(self.variables_schema, str):
            return json.loads(self.variables_schema)
        return self.variables_schema or {}

    def validate_variables(self, values: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate provided variable values against the schema.

        Args:
            values: Dictionary of variable name -> value

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors: list[str] = []
        schema = self.get_variables()

        # Check required variables
        for var_name, var_def in schema.items():
            if var_def.get("required", False) and var_name not in values:
                if "default" not in var_def:
                    errors.append(f"Required variable '{var_name}' is missing")

        # Validate types
        for var_name, value in values.items():
            if var_name not in schema:
                continue  # Extra variables are allowed

            var_def = schema[var_name]
            var_type = var_def.get("type", "string")

            if var_type == "integer":
                if not isinstance(value, int) and not (isinstance(value, str) and value.isdigit()):
                    errors.append(f"Variable '{var_name}' must be an integer")

            elif var_type == "boolean":
                if not isinstance(value, bool) and value not in (
                    "true",
                    "false",
                    "True",
                    "False",
                    "1",
                    "0",
                ):
                    errors.append(f"Variable '{var_name}' must be a boolean")

            elif var_type == "ipaddress":
                try:
                    ip_module.ip_address(str(value))
                except ValueError:
                    errors.append(f"Variable '{var_name}' must be a valid IP address")

            elif var_type == "list":
                if not isinstance(value, list):
                    if isinstance(value, str):
                        # Try to parse as comma-separated
                        pass  # Allow string that can be split
                    else:
                        errors.append(f"Variable '{var_name}' must be a list")

        return (len(errors) == 0, errors)

    def render(self, variables: dict[str, Any]) -> str:
        """Render the template with provided variables.

        Args:
            variables: Dictionary of variable values

        Returns:
            Rendered configuration text

        Raises:
            ValueError: If variable validation fails
            jinja2.TemplateError: If template rendering fails
        """
        from jinja2 import Environment, BaseLoader, StrictUndefined

        is_valid, errors = self.validate_variables(variables)
        if not is_valid:
            raise ValueError(f"Variable validation failed: {'; '.join(errors)}")

        # Merge with defaults
        schema = self.get_variables()
        merged_vars = {}
        for var_name, var_def in schema.items():
            if var_name in variables:
                merged_vars[var_name] = variables[var_name]
            elif "default" in var_def:
                merged_vars[var_name] = var_def["default"]

        # Add any extra variables not in schema
        for var_name, value in variables.items():
            if var_name not in merged_vars:
                merged_vars[var_name] = value

        env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
        template = env.from_string(self.template_content)
        return template.render(**merged_vars)


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

        def sanitize_path_component(name: str) -> str:
            """Sanitize a path component to prevent traversal attacks."""
            # Remove path separators and parent directory references
            sanitized = name.replace("/", "_").replace("\\", "_")
            # Remove any ".." sequences that could cause path traversal
            sanitized = sanitized.replace("..", "__")
            # Remove leading/trailing dots and spaces
            sanitized = sanitized.strip(". ")
            return sanitized or "unknown"

        hostname = sanitize_path_component(device.hostname)

        if self.path_structure == "by_customer":
            customer = sanitize_path_component(customer_name or device.customer.name)
            return f"{customer}/{hostname}/config.txt"
        elif self.path_structure == "by_site":
            site = sanitize_path_component(device.site or "unknown")
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


class ConfigDrift(models.Model):
    """Track configuration drift between consecutive snapshots."""

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="config_drifts",
        help_text="Device this drift analysis belongs to",
    )
    snapshot_from = models.ForeignKey(
        ConfigSnapshot,
        on_delete=models.CASCADE,
        related_name="drifts_as_from",
        help_text="Earlier snapshot in comparison",
    )
    snapshot_to = models.ForeignKey(
        ConfigSnapshot,
        on_delete=models.CASCADE,
        related_name="drifts_as_to",
        help_text="Later snapshot in comparison",
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    additions = models.IntegerField(
        default=0, help_text="Number of lines added"
    )
    deletions = models.IntegerField(
        default=0, help_text="Number of lines deleted"
    )
    changes = models.IntegerField(
        default=0, help_text="Number of lines changed"
    )
    total_lines = models.IntegerField(
        default=0, help_text="Total lines in diff output"
    )
    has_changes = models.BooleanField(
        default=False, help_text="Whether any changes were detected"
    )
    diff_summary = models.TextField(
        blank=True, help_text="Summary of major changes"
    )
    triggered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_drifts",
        help_text="User who triggered the backup that created this drift",
    )

    class Meta:
        indexes = [
            models.Index(fields=["device"]),
            models.Index(fields=["detected_at"]),
            models.Index(fields=["has_changes"]),
        ]
        ordering = ["-detected_at"]
        unique_together = ("snapshot_from", "snapshot_to")

    def __str__(self) -> str:  # pragma: no cover
        return f"Drift {self.id} for {self.device.hostname}"

    def get_change_magnitude(self) -> str:
        """Return a human-readable change magnitude."""
        total = self.additions + self.deletions
        if total == 0:
            return "No changes"
        elif total < 10:
            return "Minor changes"
        elif total < 50:
            return "Moderate changes"
        else:
            return "Major changes"


class DriftAlert(models.Model):
    """Alert for unexpected configuration changes."""

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("ignored", "Ignored"),
    ]

    drift = models.ForeignKey(
        ConfigDrift,
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="Associated drift analysis",
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="info",
        help_text="Alert severity level",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        help_text="Alert status",
    )
    message = models.TextField(
        help_text="Alert message describing the change"
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_drift_alerts",
    )
    acknowledged_at = models.DateTimeField(
        null=True, blank=True
    )
    resolution_notes = models.TextField(
        blank=True, help_text="Notes about alert resolution"
    )

    class Meta:
        indexes = [
            models.Index(fields=["severity"]),
            models.Index(fields=["status"]),
            models.Index(fields=["detected_at"]),
        ]
        ordering = ["-detected_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Alert {self.id} - {self.severity} ({self.status})"

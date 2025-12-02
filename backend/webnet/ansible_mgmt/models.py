"""Models for Ansible playbook management."""

from django.db import models


class AnsibleConfig(models.Model):
    """Ansible configuration settings for a customer."""

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="ansible_config",
        help_text="Customer this Ansible configuration belongs to",
    )
    ansible_cfg_content = models.TextField(
        blank=True,
        default="",
        help_text="Custom ansible.cfg content (optional)",
    )
    vault_password = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Vault password for Ansible Vault. "
            "WARNING: Currently stored as plain text. "
            "Consider using the same encryption mechanism as device credentials for production use."
        ),
    )
    collections = models.JSONField(
        default=list,
        blank=True,
        help_text="List of Ansible collections to install (e.g., ['cisco.ios', 'ansible.netcommon'])",
    )
    environment_vars = models.JSONField(
        default=dict,
        blank=True,
        help_text="Environment variables for Ansible execution",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ansible Configuration"
        verbose_name_plural = "Ansible Configurations"

    def __str__(self) -> str:  # pragma: no cover
        return f"Ansible Config for {self.customer.name}"


class Playbook(models.Model):
    """Ansible playbook storage."""

    SOURCE_CHOICES = (
        ("inline", "Inline Content"),
        ("git", "Git Repository"),
        ("upload", "File Upload"),
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="playbooks",
        help_text="Customer this playbook belongs to",
    )
    name = models.CharField(max_length=200, help_text="Playbook name")
    description = models.TextField(blank=True, default="", help_text="Playbook description")
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="inline",
        help_text="Source type of the playbook",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Inline playbook content (YAML)",
    )
    git_repo_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Git repository URL (for git source)",
    )
    git_branch = models.CharField(
        max_length=100,
        blank=True,
        default="main",
        help_text="Git branch name",
    )
    git_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Path to playbook within git repository",
    )
    uploaded_file = models.FileField(
        upload_to="playbooks/%Y/%m/",
        blank=True,
        null=True,
        help_text="Uploaded playbook file (for upload source)",
    )
    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default variables for playbook execution",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorizing playbooks",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this playbook is enabled for execution",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_playbooks",
        help_text="User who created this playbook",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["name"]),
            models.Index(fields=["enabled"]),
        ]
        unique_together = [["customer", "name"]]
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.customer.name})"

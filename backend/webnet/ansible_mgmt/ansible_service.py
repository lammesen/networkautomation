"""Service for Ansible inventory generation and playbook execution."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from webnet.devices.models import Device

logger = logging.getLogger(__name__)


def _sanitize_git_url(url: str) -> str:
    """Sanitize Git URL by removing credentials for logging.

    Args:
        url: Git repository URL that may contain embedded credentials

    Returns:
        Sanitized URL with credentials removed
    """
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            # Remove credentials from URL for logging
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc += f":{parsed.port}"
            sanitized = parsed._replace(netloc=netloc)
            return urlunparse(sanitized)
    except Exception:
        # If parsing fails, return a generic message
        return "[URL]"
    return url


def fetch_playbook_from_git(
    git_repo_url: str,
    git_branch: str,
    git_path: str,
    timeout: int = 60,
) -> tuple[bool, str, str]:
    """Fetch playbook content from a Git repository.

    Args:
        git_repo_url: Git repository URL (HTTPS or SSH)
        git_branch: Branch name to fetch from
        git_path: Path to playbook file within the repository
        timeout: Operation timeout in seconds

    Returns:
        Tuple of (success, content, error_message)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        repo_dir = tmppath / "repo"

        try:
            # Clone the repository (shallow clone for efficiency)
            logger.info(
                f"Cloning Git repository: {_sanitize_git_url(git_repo_url)} (branch: {git_branch})"
            )
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    git_branch,
                    "--single-branch",
                    git_repo_url,
                    str(repo_dir),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Failed to clone repository"
                logger.error(f"Git clone failed: {error_msg}")
                return False, "", error_msg

            # Read the playbook file with path traversal protection
            playbook_file = repo_dir / git_path
            # Resolve to canonical path and ensure it's within repo_dir
            resolved_path = playbook_file.resolve()
            repo_dir_resolved = repo_dir.resolve()
            if not str(resolved_path).startswith(str(repo_dir_resolved)):
                error_msg = f"Invalid path: {git_path} (path traversal detected)"
                logger.error(error_msg)
                return False, "", error_msg
            if not resolved_path.exists():
                error_msg = f"Playbook file not found at path: {git_path}"
                logger.error(error_msg)
                return False, "", error_msg

            content = resolved_path.read_text()
            logger.info(f"Successfully fetched playbook from Git: {len(content)} bytes")
            return True, content, ""

        except subprocess.TimeoutExpired:
            error_msg = f"Git clone timed out after {timeout} seconds"
            logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error fetching playbook from Git: {str(e)}"
            logger.exception(error_msg)
            return False, "", error_msg


def generate_ansible_inventory(
    filters: dict | None = None, customer_id: int | None = None
) -> dict[str, Any]:
    """Generate Ansible inventory from webnet devices.

    Returns inventory in JSON format compatible with Ansible.
    Devices are grouped by site, role, and vendor.
    """
    qs = Device.objects.select_related("credential", "customer").filter(enabled=True)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if filters:
        if filters.get("device_ids"):
            qs = qs.filter(id__in=filters["device_ids"])
        if filters.get("vendor"):
            qs = qs.filter(vendor=filters["vendor"])
        if filters.get("site"):
            qs = qs.filter(site=filters["site"])
        if filters.get("role"):
            qs = qs.filter(role=filters["role"])

    inventory: dict[str, Any] = {
        "_meta": {"hostvars": {}},
        "all": {"children": ["ungrouped"]},
    }

    # Track groups
    site_groups: set[str] = set()
    role_groups: set[str] = set()
    vendor_groups: set[str] = set()

    for dev in qs:
        if not dev.credential:
            logger.warning(f"Device {dev.hostname} has no credential, skipping")
            continue
        cred = dev.credential
        hostname = dev.hostname

        # Add host variables
        # Note: Passwords are stored encrypted in the database but must be
        # decrypted for Ansible execution. Consider using SSH keys for enhanced security.
        inventory["_meta"]["hostvars"][hostname] = {
            "ansible_host": dev.mgmt_ip,
            "ansible_user": cred.username,
            "ansible_password": cred.password or "",
            "ansible_network_os": dev.platform,
            "device_id": dev.id,
            "customer_id": dev.customer_id,
            "vendor": dev.vendor,
            "platform": dev.platform,
            "role": dev.role or "",
            "site": dev.site or "",
        }

        # Group by site
        if dev.site:
            site_group = f"site_{dev.site}"
            site_groups.add(site_group)
            if site_group not in inventory:
                inventory[site_group] = {"hosts": []}
            inventory[site_group]["hosts"].append(hostname)

        # Group by role
        if dev.role:
            role_group = f"role_{dev.role}"
            role_groups.add(role_group)
            if role_group not in inventory:
                inventory[role_group] = {"hosts": []}
            inventory[role_group]["hosts"].append(hostname)

        # Group by vendor
        if dev.vendor:
            vendor_group = f"vendor_{dev.vendor}"
            vendor_groups.add(vendor_group)
            if vendor_group not in inventory:
                inventory[vendor_group] = {"hosts": []}
            inventory[vendor_group]["hosts"].append(hostname)

    # Create parent groups for organization
    if site_groups:
        inventory["all_sites"] = {"children": sorted(site_groups)}
        inventory["all"]["children"].append("all_sites")

    if role_groups:
        inventory["all_roles"] = {"children": sorted(role_groups)}
        inventory["all"]["children"].append("all_roles")

    if vendor_groups:
        inventory["all_vendors"] = {"children": sorted(vendor_groups)}
        inventory["all"]["children"].append("all_vendors")

    return inventory


def execute_ansible_playbook(
    playbook_content: str,
    inventory: dict[str, Any],
    extra_vars: dict | None = None,
    limit: str | None = None,
    tags: list[str] | None = None,
    ansible_cfg_content: str | None = None,
    vault_password: str | None = None,
    environment_vars: dict | None = None,
    timeout: int = 3600,
) -> tuple[int, str, str]:
    """Execute Ansible playbook with given inventory.

    Args:
        playbook_content: Playbook YAML content
        inventory: Ansible inventory dict
        extra_vars: Extra variables to pass to playbook
        limit: Limit execution to specific hosts (validated for safety)
        tags: Ansible tags to run
        ansible_cfg_content: Custom ansible.cfg content
        vault_password: Vault password for encrypted vars
        environment_vars: Environment variables for execution
        timeout: Execution timeout in seconds (default: 3600)

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    import re

    # Validate limit parameter to prevent command injection
    if limit:
        # Only allow safe characters: alphanumeric, dots, hyphens, wildcards, commas, colons, brackets
        if not re.match(r"^[a-zA-Z0-9._\-*,:\[\]]+$", limit):
            logger.error(f"Invalid limit pattern: {limit}")
            return 1, "", f"Invalid limit pattern: {limit}"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Write playbook
        playbook_file = tmppath / "playbook.yml"
        playbook_file.write_text(playbook_content)

        # Write inventory
        inventory_file = tmppath / "inventory.json"
        inventory_file.write_text(json.dumps(inventory))

        # Write ansible.cfg if provided
        if ansible_cfg_content:
            cfg_file = tmppath / "ansible.cfg"
            cfg_file.write_text(ansible_cfg_content)

        # Write vault password if provided
        vault_password_file = None
        if vault_password:
            vault_password_file = tmppath / "vault_pass.txt"
            vault_password_file.write_text(vault_password)
            vault_password_file.chmod(0o600)

        # Build ansible-playbook command
        cmd = [
            "ansible-playbook",
            str(playbook_file),
            "-i",
            str(inventory_file),
        ]

        if extra_vars:
            cmd.extend(["-e", json.dumps(extra_vars)])

        if limit:
            cmd.extend(["--limit", limit])

        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        if vault_password_file:
            cmd.extend(["--vault-password-file", str(vault_password_file)])

        # Set environment variables
        env = os.environ.copy()
        if ansible_cfg_content:
            env["ANSIBLE_CONFIG"] = str(tmppath / "ansible.cfg")
        if environment_vars:
            env.update(environment_vars)

        # Note: Host key checking is disabled for automation.
        # In production, consider using SSH key management or host key verification.
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"

        # Execute playbook
        try:
            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Playbook execution timed out after {timeout} seconds"
        except Exception as e:
            logger.exception("Error executing Ansible playbook")
            return 1, "", str(e)

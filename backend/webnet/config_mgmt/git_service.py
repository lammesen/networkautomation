"""Git integration service for configuration backup export.

This module provides a service for syncing config snapshots to a Git repository.
It supports both HTTPS (token-based) and SSH authentication methods.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from webnet.config_mgmt.models import ConfigSnapshot, GitRepository
    from webnet.jobs.models import Job

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a Git sync operation."""

    success: bool
    commit_hash: str | None = None
    files_synced: int = 0
    message: str = ""
    error: str | None = None


class GitService:
    """Service for syncing config snapshots to Git repositories.

    This service handles:
    - Cloning/pulling the repository
    - Writing config files with proper directory structure
    - Committing changes with meaningful messages
    - Pushing changes to the remote
    - Handling merge conflicts gracefully

    Supports authentication via:
    - HTTPS with access token
    - SSH with private key
    """

    def __init__(self, repository: "GitRepository"):
        """Initialize the Git service for a repository.

        Args:
            repository: The GitRepository model instance to sync to
        """
        self.repository = repository
        self._temp_dir: Path | None = None
        self._ssh_key_file: Path | None = None

    def sync_snapshots(
        self,
        snapshots: list["ConfigSnapshot"],
        job: "Job | None" = None,
        commit_message: str | None = None,
    ) -> SyncResult:
        """Sync config snapshots to the Git repository.

        Args:
            snapshots: List of ConfigSnapshot instances to sync
            job: Optional Job instance for audit trail
            commit_message: Optional custom commit message

        Returns:
            SyncResult with success status and details
        """
        from webnet.config_mgmt.models import GitSyncLog

        if not snapshots:
            return SyncResult(success=True, message="No snapshots to sync")

        if not self.repository.enabled:
            return SyncResult(success=False, message="Git sync is disabled for this repository")

        # Create sync log entry
        sync_log = GitSyncLog.objects.create(
            repository=self.repository,
            job=job,
            status="running",
            message="Starting sync...",
        )

        try:
            # Prepare workspace
            self._setup_workspace()

            # Clone or pull the repository
            self._clone_or_pull()

            # Write config files
            files_written = self._write_config_files(snapshots)

            if files_written == 0:
                sync_log.status = "success"
                sync_log.message = "No changes to commit"
                sync_log.finished_at = timezone.now()
                sync_log.save()
                return SyncResult(success=True, message="No changes to commit")

            # Commit changes
            commit_msg = commit_message or self._generate_commit_message(snapshots, job)
            commit_hash = self._commit_changes(commit_msg)

            if not commit_hash:
                sync_log.status = "success"
                sync_log.message = "No changes to commit (files unchanged)"
                sync_log.finished_at = timezone.now()
                sync_log.save()
                return SyncResult(success=True, message="No changes to commit")

            # Push to remote
            self._push_changes()

            # Update sync log and repository
            sync_log.status = "success"
            sync_log.commit_hash = commit_hash
            sync_log.files_synced = files_written
            sync_log.message = commit_msg
            sync_log.finished_at = timezone.now()
            sync_log.save()

            # Update snapshots with git sync info
            for snapshot in snapshots:
                snapshot.git_synced = True
                snapshot.git_commit_hash = commit_hash
                snapshot.git_sync_log = sync_log
                snapshot.save(update_fields=["git_synced", "git_commit_hash", "git_sync_log"])

            # Update repository last sync status
            self.repository.last_sync_at = timezone.now()
            self.repository.last_sync_status = "success"
            self.repository.last_sync_message = f"Synced {files_written} configs"
            self.repository.save(
                update_fields=["last_sync_at", "last_sync_status", "last_sync_message"]
            )

            return SyncResult(
                success=True,
                commit_hash=commit_hash,
                files_synced=files_written,
                message=commit_msg,
            )

        except Exception as e:
            error_msg = str(e)
            logger.exception("Git sync failed for repository %s", self.repository.id)

            # Update sync log
            sync_log.status = "failed"
            sync_log.message = error_msg
            sync_log.finished_at = timezone.now()
            sync_log.save()

            # Update repository last sync status
            self.repository.last_sync_at = timezone.now()
            self.repository.last_sync_status = "failed"
            self.repository.last_sync_message = error_msg
            self.repository.save(
                update_fields=["last_sync_at", "last_sync_status", "last_sync_message"]
            )

            return SyncResult(success=False, error=error_msg)

        finally:
            self._cleanup_workspace()

    def test_connection(self) -> SyncResult:
        """Test the Git repository connection.

        Returns:
            SyncResult indicating if the connection is successful
        """
        try:
            self._setup_workspace()

            # Try to clone (fetch-only) to verify credentials
            env = self._get_git_env()
            remote_url = self._get_authenticated_url()

            result = subprocess.run(
                ["git", "ls-remote", remote_url],
                cwd=self._temp_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return SyncResult(
                    success=False,
                    error=f"Connection failed: {result.stderr.strip()}",
                )

            return SyncResult(success=True, message="Connection successful")

        except subprocess.TimeoutExpired:
            return SyncResult(success=False, error="Connection timed out")
        except Exception as e:
            return SyncResult(success=False, error=str(e))
        finally:
            self._cleanup_workspace()

    def get_recent_commits(self, limit: int = 10) -> list[dict]:
        """Get recent commits from the repository.

        Args:
            limit: Maximum number of commits to return

        Returns:
            List of commit dictionaries with hash, message, author, date
        """
        try:
            self._setup_workspace()
            self._clone_or_pull()

            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-{limit}",
                    "--format=%H|%s|%an|%aI",
                ],
                cwd=self._temp_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "message": parts[1],
                            "author": parts[2],
                            "date": parts[3],
                        }
                    )
            return commits

        except Exception as e:
            logger.exception("Failed to get recent commits: %s", e)
            return []
        finally:
            self._cleanup_workspace()

    def _setup_workspace(self) -> None:
        """Set up temporary workspace for Git operations."""
        self._temp_dir = Path(tempfile.mkdtemp(prefix="webnet_git_"))

        # Set up SSH key if using SSH auth
        if self.repository.auth_type == "ssh_key" and self.repository.ssh_private_key:
            self._ssh_key_file = self._temp_dir / "id_rsa"
            self._ssh_key_file.write_text(self.repository.ssh_private_key)
            os.chmod(self._ssh_key_file, 0o600)

    def _cleanup_workspace(self) -> None:
        """Clean up temporary workspace."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = None
        self._ssh_key_file = None

    def _get_git_env(self) -> dict:
        """Get environment variables for Git commands."""
        env = os.environ.copy()

        if self._ssh_key_file:
            # Use custom SSH command with our private key
            ssh_cmd = f"ssh -i {self._ssh_key_file} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            env["GIT_SSH_COMMAND"] = ssh_cmd

        return env

    def _get_authenticated_url(self) -> str:
        """Get the remote URL with authentication embedded."""
        url = self.repository.remote_url

        if self.repository.auth_type == "token" and self.repository.auth_token:
            # For HTTPS URLs, embed the token
            if url.startswith("https://"):
                # Format: https://token@github.com/user/repo.git
                # or https://x-access-token:token@github.com/user/repo.git for GitHub
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(url)
                token = self.repository.auth_token

                # GitHub uses x-access-token as username
                if "github.com" in parsed.netloc:
                    netloc = f"x-access-token:{token}@{parsed.netloc}"
                else:
                    # GitLab and others typically use oauth2 or the token directly
                    netloc = f"oauth2:{token}@{parsed.netloc}"

                url = urlunparse(parsed._replace(netloc=netloc))

        return url

    def _clone_or_pull(self) -> None:
        """Clone the repository or pull if already cloned."""
        if not self._temp_dir:
            raise RuntimeError("Workspace not set up")

        repo_dir = self._temp_dir / "repo"
        env = self._get_git_env()
        remote_url = self._get_authenticated_url()

        # Clone the repository
        result = subprocess.run(
            ["git", "clone", "--depth=1", "-b", self.repository.branch, remote_url, str(repo_dir)],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr.strip()}")

        # Update temp_dir to point to the cloned repo
        self._temp_dir = repo_dir

        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.email", "webnet@automation.local"],
            cwd=self._temp_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Webnet Config Backup"],
            cwd=self._temp_dir,
            check=True,
        )

    def _write_config_files(self, snapshots: list["ConfigSnapshot"]) -> int:
        """Write config snapshots to files.

        Args:
            snapshots: List of ConfigSnapshot instances

        Returns:
            Number of files written
        """
        if not self._temp_dir:
            raise RuntimeError("Workspace not set up")

        files_written = 0

        for snapshot in snapshots:
            file_path = self._temp_dir / self.repository.get_config_path(snapshot.device)

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config text
            file_path.write_text(snapshot.config_text)
            files_written += 1

            # Add metadata file with snapshot info
            metadata_path = file_path.with_suffix(".meta.json")
            import json

            metadata = {
                "snapshot_id": snapshot.id,
                "device_hostname": snapshot.device.hostname,
                "device_ip": snapshot.device.mgmt_ip,
                "created_at": snapshot.created_at.isoformat(),
                "source": snapshot.source,
                "config_hash": snapshot.hash,
            }
            metadata_path.write_text(json.dumps(metadata, indent=2))

        return files_written

    def _commit_changes(self, message: str) -> str | None:
        """Commit changes and return the commit hash.

        Args:
            message: Commit message

        Returns:
            Commit hash if changes were committed, None otherwise
        """
        if not self._temp_dir:
            raise RuntimeError("Workspace not set up")

        # Add all changes
        subprocess.run(["git", "add", "-A"], cwd=self._temp_dir, check=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self._temp_dir,
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            return None  # No changes

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self._temp_dir,
            check=True,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self._temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def _push_changes(self) -> None:
        """Push committed changes to the remote."""
        if not self._temp_dir:
            raise RuntimeError("Workspace not set up")

        env = self._get_git_env()
        remote_url = self._get_authenticated_url()

        # Update remote URL with auth (in case clone used cached credentials)
        subprocess.run(
            ["git", "remote", "set-url", "origin", remote_url],
            cwd=self._temp_dir,
            env=env,
            check=True,
        )

        result = subprocess.run(
            ["git", "push", "origin", self.repository.branch],
            cwd=self._temp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git push failed: {result.stderr.strip()}")

    def _generate_commit_message(
        self, snapshots: list["ConfigSnapshot"], job: "Job | None" = None
    ) -> str:
        """Generate a meaningful commit message.

        Args:
            snapshots: List of snapshots being synced
            job: Optional job that triggered the sync

        Returns:
            Commit message string
        """
        device_count = len(set(s.device_id for s in snapshots))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        msg_parts = [f"Config backup: {device_count} device(s)"]

        if job:
            msg_parts.append(f"Job ID: {job.id}")
            if job.user:
                msg_parts.append(f"User: {job.user.username}")

        msg_parts.append(f"Timestamp: {timestamp}")

        # List devices (up to 10)
        devices = sorted(set(s.device.hostname for s in snapshots))
        if len(devices) <= 10:
            msg_parts.append(f"Devices: {', '.join(devices)}")
        else:
            msg_parts.append(f"Devices: {', '.join(devices[:10])} (+{len(devices) - 10} more)")

        return "\n".join(msg_parts)


def sync_configs_to_git(
    customer_id: int,
    snapshot_ids: list[int] | None = None,
    job: "Job | None" = None,
) -> SyncResult:
    """Convenience function to sync configs to Git for a customer.

    Args:
        customer_id: ID of the customer whose configs to sync
        snapshot_ids: Optional list of specific snapshot IDs to sync.
                      If None, syncs all unsynced snapshots.
        job: Optional job for audit trail

    Returns:
        SyncResult with success status and details
    """
    from webnet.config_mgmt.models import ConfigSnapshot, GitRepository

    try:
        repository = GitRepository.objects.select_related("customer").get(customer_id=customer_id)
    except GitRepository.DoesNotExist:
        return SyncResult(success=False, error="No Git repository configured for this customer")

    if not repository.enabled:
        return SyncResult(success=False, error="Git sync is disabled for this customer")

    # Get snapshots to sync
    if snapshot_ids:
        snapshots = list(
            ConfigSnapshot.objects.filter(
                id__in=snapshot_ids, device__customer_id=customer_id
            ).select_related("device", "device__customer")
        )
    else:
        # Get all unsynced snapshots for this customer
        snapshots = list(
            ConfigSnapshot.objects.filter(
                device__customer_id=customer_id, git_synced=False
            ).select_related("device", "device__customer")
        )

    if not snapshots:
        return SyncResult(success=True, message="No snapshots to sync")

    service = GitService(repository)
    return service.sync_snapshots(snapshots, job=job)

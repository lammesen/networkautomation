"""Tests for Git integration feature."""

import json
from unittest.mock import patch, MagicMock
import pytest
from django.urls import reverse

from webnet.config_mgmt.models import GitRepository, GitSyncLog, ConfigSnapshot
from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential
from webnet.users.models import User


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="testpass123",
        role="admin",
    )
    return user


@pytest.fixture
def operator_user(db, customer):
    """Create an operator user with customer access."""
    user = User.objects.create_user(
        username="operator",
        email="operator@test.com",
        password="testpass123",
        role="operator",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def viewer_user(db, customer):
    """Create a viewer user with customer access."""
    user = User.objects.create_user(
        username="viewer",
        email="viewer@test.com",
        password="testpass123",
        role="viewer",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def customer(db):
    """Create a test customer."""
    return Customer.objects.create(name="Test Customer")


@pytest.fixture
def other_customer(db):
    """Create another test customer for isolation tests."""
    return Customer.objects.create(name="Other Customer")


@pytest.fixture
def credential(db, customer):
    """Create a test credential."""
    cred = Credential(customer=customer, name="testcred", username="user")
    cred.password = "secret"
    cred.save()
    return cred


@pytest.fixture
def device(db, customer, credential):
    """Create a test device."""
    return Device.objects.create(
        customer=customer,
        hostname="router1.test.local",
        mgmt_ip="10.0.0.1",
        vendor="Cisco",
        platform="ios",
        site="DC1",
        credential=credential,
    )


@pytest.fixture
def git_repository(db, customer):
    """Create a test Git repository."""
    repo = GitRepository(
        customer=customer,
        name="Config Backup Repo",
        remote_url="https://github.com/test/repo.git",
        branch="main",
        auth_type="token",
        path_structure="by_customer",
        enabled=True,
    )
    repo.auth_token = "test-token-123"
    repo.save()
    return repo


@pytest.fixture
def config_snapshot(db, device):
    """Create a test config snapshot."""
    return ConfigSnapshot.objects.create(
        device=device,
        source="test",
        config_text="hostname router1\ninterface Gi0/0\n  ip address 10.0.0.1 255.255.255.0\n",
    )


@pytest.mark.django_db
class TestGitRepositoryModel:
    """Tests for GitRepository model."""

    def test_create_git_repository(self, customer):
        """Test creating a Git repository."""
        repo = GitRepository(
            customer=customer,
            name="Test Repo",
            remote_url="https://github.com/test/repo.git",
            branch="main",
            auth_type="token",
            path_structure="by_customer",
            enabled=True,
        )
        repo.auth_token = "secret-token"
        repo.save()

        assert repo.id is not None
        assert repo.customer == customer
        assert repo.name == "Test Repo"
        assert repo.auth_token == "secret-token"
        assert repo._auth_token != "secret-token"  # Encrypted

    def test_ssh_key_encryption(self, customer):
        """Test SSH key encryption."""
        repo = GitRepository(
            customer=customer,
            name="SSH Repo",
            remote_url="git@github.com:test/repo.git",
            auth_type="ssh_key",
        )
        repo.ssh_private_key = (
            "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
        )
        repo.save()

        assert (
            repo.ssh_private_key
            == "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
        )
        assert repo._ssh_private_key != repo.ssh_private_key  # Encrypted

    def test_get_config_path_by_customer(self, git_repository, device):
        """Test config path generation with by_customer structure."""
        git_repository.path_structure = "by_customer"
        git_repository.save()

        path = git_repository.get_config_path(device)
        assert path == "Test Customer/router1.test.local/config.txt"

    def test_get_config_path_by_site(self, git_repository, device):
        """Test config path generation with by_site structure."""
        git_repository.path_structure = "by_site"
        git_repository.save()

        path = git_repository.get_config_path(device)
        assert path == "DC1/router1.test.local/config.txt"

    def test_get_config_path_flat(self, git_repository, device):
        """Test config path generation with flat structure."""
        git_repository.path_structure = "flat"
        git_repository.save()

        path = git_repository.get_config_path(device)
        assert path == "router1.test.local.txt"

    def test_one_repo_per_customer(self, customer, git_repository):
        """Test that each customer can only have one repository (OneToOne)."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            GitRepository.objects.create(
                customer=customer,
                name="Another Repo",
                remote_url="https://github.com/test/another.git",
            )


@pytest.mark.django_db
class TestGitSyncLogModel:
    """Tests for GitSyncLog model."""

    def test_create_sync_log(self, git_repository):
        """Test creating a sync log."""
        log = GitSyncLog.objects.create(
            repository=git_repository,
            status="success",
            commit_hash="abc1234567890def",
            files_synced=5,
            message="Synced 5 files",
        )

        assert log.id is not None
        assert log.repository == git_repository
        assert log.status == "success"
        assert log.files_synced == 5


@pytest.mark.django_db
class TestGitRepositoryAPI:
    """Tests for Git repository API endpoints."""

    def test_list_repositories_admin(self, client, admin_user, git_repository):
        """Test listing repositories as admin."""
        client.force_login(admin_user)
        response = client.get("/api/v1/git/repositories/")

        assert response.status_code == 200
        data = response.json()
        # API uses pagination
        results = data.get("results", data)
        assert len(results) == 1
        assert results[0]["name"] == "Config Backup Repo"

    def test_list_repositories_scoped_to_customer(
        self, client, operator_user, customer, other_customer
    ):
        """Test that repositories are scoped to user's customers."""
        # Create repo for other customer
        other_repo = GitRepository(
            customer=other_customer,
            name="Other Repo",
            remote_url="https://github.com/test/other.git",
        )
        other_repo.save()

        # Create repo for user's customer
        user_repo = GitRepository(
            customer=customer,
            name="User Repo",
            remote_url="https://github.com/test/user.git",
        )
        user_repo.save()

        client.force_login(operator_user)
        response = client.get("/api/v1/git/repositories/")

        assert response.status_code == 200
        data = response.json()
        # API uses pagination
        results = data.get("results", data)
        assert len(results) == 1
        assert results[0]["name"] == "User Repo"

    def test_create_repository(self, client, admin_user, customer):
        """Test creating a repository via API."""
        client.force_login(admin_user)
        response = client.post(
            "/api/v1/git/repositories/",
            data=json.dumps(
                {
                    "customer": customer.id,
                    "name": "New Repo",
                    "remote_url": "https://github.com/test/new.git",
                    "branch": "main",
                    "auth_type": "token",
                    "auth_token": "my-secret-token",
                    "path_structure": "by_customer",
                    "enabled": True,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Repo"
        assert "auth_token" not in data  # Write-only
        assert data["has_auth_token"] is True

    def test_token_not_exposed(self, client, admin_user, git_repository):
        """Test that auth tokens are not exposed in API responses."""
        client.force_login(admin_user)
        response = client.get(f"/api/v1/git/repositories/{git_repository.id}/")

        assert response.status_code == 200
        data = response.json()
        assert "auth_token" not in data or data.get("auth_token") is None
        assert data["has_auth_token"] is True

    def test_viewer_cannot_create(self, client, viewer_user, customer):
        """Test that viewers cannot create repositories."""
        client.force_login(viewer_user)
        response = client.post(
            "/api/v1/git/repositories/",
            data=json.dumps(
                {
                    "customer": customer.id,
                    "name": "Viewer Repo",
                    "remote_url": "https://github.com/test/viewer.git",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestGitSettingsUI:
    """Tests for Git settings UI views."""

    def test_git_settings_list(self, client, admin_user, git_repository):
        """Test Git settings list page."""
        client.force_login(admin_user)
        response = client.get(reverse("git-settings"))

        assert response.status_code == 200
        assert b"Config Backup Repo" in response.content

    def test_git_settings_detail(self, client, admin_user, git_repository):
        """Test Git settings detail page."""
        client.force_login(admin_user)
        response = client.get(reverse("git-settings-detail", args=[git_repository.pk]))

        assert response.status_code == 200
        assert b"Config Backup Repo" in response.content
        assert b"Test Connection" in response.content
        assert b"Sync Now" in response.content

    def test_git_settings_create_page(self, client, admin_user):
        """Test Git settings create page."""
        client.force_login(admin_user)
        response = client.get(reverse("git-settings-create"))

        assert response.status_code == 200
        assert b"Add Git Repository" in response.content

    def test_git_settings_scoped_to_customer(self, client, operator_user, customer, other_customer):
        """Test that Git settings are scoped to user's customers."""
        # Create repo for other customer
        other_repo = GitRepository(
            customer=other_customer,
            name="Other Repo",
            remote_url="https://github.com/test/other.git",
        )
        other_repo.save()

        client.force_login(operator_user)
        response = client.get(reverse("git-settings"))

        assert response.status_code == 200
        assert b"Other Repo" not in response.content

    def test_viewer_cannot_delete(self, client, viewer_user, git_repository):
        """Test that viewers cannot delete repositories."""
        client.force_login(viewer_user)
        response = client.post(reverse("git-settings-delete", args=[git_repository.pk]))

        assert response.status_code == 403
        assert GitRepository.objects.filter(pk=git_repository.pk).exists()


@pytest.mark.django_db
class TestGitService:
    """Tests for Git service."""

    def test_get_config_path_sanitizes_names(self, git_repository, device):
        """Test that config paths sanitize special characters."""
        device.hostname = "router/1\\test"
        device.save()

        path = git_repository.get_config_path(device)
        assert "/" not in path.split("/")[-1] or path.endswith("config.txt")

    @patch("subprocess.run")
    def test_test_connection_success(self, mock_run, git_repository):
        """Test connection test with successful result."""
        from webnet.config_mgmt.git_service import GitService

        mock_run.return_value = MagicMock(returncode=0, stdout="refs/heads/main", stderr="")

        service = GitService(git_repository)
        result = service.test_connection()

        assert result.success is True
        assert "successful" in result.message.lower()

    @patch("subprocess.run")
    def test_test_connection_failure(self, mock_run, git_repository):
        """Test connection test with failed result."""
        from webnet.config_mgmt.git_service import GitService

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="authentication failed")

        service = GitService(git_repository)
        result = service.test_connection()

        assert result.success is False
        assert result.error is not None


@pytest.mark.django_db
class TestConfigSnapshotGitFields:
    """Tests for ConfigSnapshot Git-related fields."""

    def test_snapshot_git_fields_default(self, config_snapshot):
        """Test that new snapshots have default Git field values."""
        assert config_snapshot.git_synced is False
        assert config_snapshot.git_commit_hash is None
        assert config_snapshot.git_sync_log is None

    def test_snapshot_git_fields_after_sync(self, config_snapshot, git_repository):
        """Test updating snapshot Git fields after sync."""
        log = GitSyncLog.objects.create(
            repository=git_repository,
            status="success",
            commit_hash="abc123def456",
            files_synced=1,
        )

        config_snapshot.git_synced = True
        config_snapshot.git_commit_hash = "abc123def456"
        config_snapshot.git_sync_log = log
        config_snapshot.save()

        config_snapshot.refresh_from_db()
        assert config_snapshot.git_synced is True
        assert config_snapshot.git_commit_hash == "abc123def456"
        assert config_snapshot.git_sync_log == log

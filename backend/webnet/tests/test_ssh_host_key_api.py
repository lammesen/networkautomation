"""Tests for SSH host key API endpoints."""

import json

import pytest
from rest_framework import status

from webnet.customers.models import Customer
from webnet.devices.models import Device, SSHHostKey


@pytest.fixture
def admin_client(client, admin_user):
    """Return authenticated admin client."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def operator_client(client, operator_user):
    """Return authenticated operator client."""
    client.force_login(operator_user)
    return client


@pytest.fixture
def viewer_client(client, viewer_user):
    """Return authenticated viewer client."""
    client.force_login(viewer_user)
    return client


@pytest.fixture
def host_key(device):
    """Create a test SSH host key."""
    return SSHHostKey.objects.create(
        device=device,
        key_type=SSHHostKey.KEY_TYPE_RSA,
        public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDtest",
        fingerprint_sha256="abcd1234efgh5678",
    )


@pytest.mark.django_db
class TestSSHHostKeyAPIList:
    """Tests for listing SSH host keys."""

    def test_list_host_keys_admin(self, admin_client, host_key):
        """Test admin can list host keys."""
        response = admin_client.get("/api/v1/ssh/host-keys/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == host_key.id
        assert data["results"][0]["device_hostname"] == host_key.device.hostname
        assert data["results"][0]["key_type"] == SSHHostKey.KEY_TYPE_RSA

    def test_list_host_keys_scoped_to_customer(self, operator_client, customer, host_key):
        """Test host keys are scoped to customer."""
        # Create another customer and device
        other_customer = Customer.objects.create(name="Other Customer")
        from webnet.devices.models import Credential

        other_cred = Credential.objects.create(
            customer=other_customer, name="other-cred", username="admin"
        )
        other_cred.password = "password"
        other_cred.save()
        other_device = Device.objects.create(
            customer=other_customer,
            hostname="other-device",
            mgmt_ip="10.0.0.1",
            vendor="cisco",
            platform="ios",
            credential=other_cred,
        )
        other_key = SSHHostKey.objects.create(
            device=other_device,
            key_type=SSHHostKey.KEY_TYPE_RSA,
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDother",
            fingerprint_sha256="other1234",
        )

        # Operator should only see keys for their customer
        response = operator_client.get("/api/v1/ssh/host-keys/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        result_ids = [r["id"] for r in data["results"]]
        assert host_key.id in result_ids
        assert other_key.id not in result_ids

    def test_list_host_keys_viewer(self, viewer_client, host_key):
        """Test viewer can list host keys."""
        response = viewer_client.get("/api/v1/ssh/host-keys/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_host_keys_filter_by_device(self, admin_client, host_key, device):
        """Test filtering host keys by device."""
        response = admin_client.get(f"/api/v1/ssh/host-keys/?device={device.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 1

    def test_list_host_keys_filter_by_verified(self, admin_client, host_key):
        """Test filtering host keys by verified status."""
        # Unverified key
        response = admin_client.get("/api/v1/ssh/host-keys/?verified=false")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 1

        # Verified keys
        response = admin_client.get("/api/v1/ssh/host-keys/?verified=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 0


@pytest.mark.django_db
class TestSSHHostKeyAPIRetrieve:
    """Tests for retrieving individual SSH host keys."""

    def test_retrieve_host_key(self, admin_client, host_key):
        """Test retrieving a specific host key."""
        response = admin_client.get(f"/api/v1/ssh/host-keys/{host_key.id}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == host_key.id
        assert data["fingerprint_display"] == f"SHA256:{host_key.fingerprint_sha256}"

    def test_retrieve_host_key_no_access(self, operator_client, host_key):
        """Test cannot retrieve host key from different customer."""
        # Create another customer and device
        other_customer = Customer.objects.create(name="Other Customer")
        from webnet.devices.models import Credential

        other_cred = Credential.objects.create(
            customer=other_customer, name="other-cred", username="admin"
        )
        other_cred.password = "password"
        other_cred.save()
        other_device = Device.objects.create(
            customer=other_customer,
            hostname="other-device",
            mgmt_ip="10.0.0.1",
            vendor="cisco",
            platform="ios",
            credential=other_cred,
        )
        other_key = SSHHostKey.objects.create(
            device=other_device,
            key_type=SSHHostKey.KEY_TYPE_RSA,
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDother",
            fingerprint_sha256="other1234",
        )

        # Should not be able to access
        response = operator_client.get(f"/api/v1/ssh/host-keys/{other_key.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSSHHostKeyAPIVerify:
    """Tests for verifying SSH host keys."""

    def test_verify_host_key(self, admin_client, host_key):
        """Test manually verifying a host key."""
        assert not host_key.verified

        response = admin_client.post(
            f"/api/v1/ssh/host-keys/{host_key.id}/verify/",
            data=json.dumps({"verified": True}),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "verified"

        host_key.refresh_from_db()
        assert host_key.verified
        assert host_key.verified_by is not None
        assert host_key.verified_at is not None

    def test_unverify_host_key(self, admin_client, host_key, admin_user):
        """Test unverifying a host key."""
        # First verify it
        from webnet.core.ssh_host_keys import SSHHostKeyService

        SSHHostKeyService.verify_key_manual(host_key, admin_user)
        assert host_key.verified

        # Now unverify
        response = admin_client.post(
            f"/api/v1/ssh/host-keys/{host_key.id}/verify/",
            data=json.dumps({"verified": False}),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_200_OK

        host_key.refresh_from_db()
        assert not host_key.verified

    def test_verify_host_key_viewer_cannot(self, viewer_client, host_key):
        """Test viewer cannot verify host keys."""
        response = viewer_client.post(
            f"/api/v1/ssh/host-keys/{host_key.id}/verify/",
            data=json.dumps({"verified": True}),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSSHHostKeyAPIDelete:
    """Tests for deleting SSH host keys."""

    def test_delete_host_key(self, admin_client, host_key):
        """Test deleting a host key."""
        key_id = host_key.id
        response = admin_client.delete(f"/api/v1/ssh/host-keys/{key_id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SSHHostKey.objects.filter(id=key_id).exists()

    def test_delete_host_key_viewer_cannot(self, viewer_client, host_key):
        """Test viewer cannot delete host keys."""
        response = viewer_client.delete(f"/api/v1/ssh/host-keys/{host_key.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert SSHHostKey.objects.filter(id=host_key.id).exists()


@pytest.mark.django_db
class TestSSHHostKeyAPIImport:
    """Tests for importing SSH host keys."""

    def test_import_host_key(self, admin_client, device):
        """Test importing a host key from known_hosts format."""
        known_hosts_line = (
            "192.168.1.1 ssh-rsa " "AAAAB3NzaC1yc2EAAAADAQABAAABAQDexamplekeydata123456789=="
        )

        response = admin_client.post(
            "/api/v1/ssh/host-keys/import/",
            data=json.dumps(
                {
                    "device_id": device.id,
                    "known_hosts_line": known_hosts_line,
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["device"] == device.id
        assert data["key_type"] == "ssh-rsa"

    def test_import_host_key_invalid_format(self, admin_client, device):
        """Test importing invalid known_hosts line."""
        response = admin_client.post(
            "/api/v1/ssh/host-keys/import/",
            data=json.dumps(
                {
                    "device_id": device.id,
                    "known_hosts_line": "invalid",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_host_key_device_not_found(self, admin_client):
        """Test importing key for non-existent device."""
        response = admin_client.post(
            "/api/v1/ssh/host-keys/import/",
            data=json.dumps(
                {
                    "device_id": 99999,
                    "known_hosts_line": "192.168.1.1 ssh-rsa AAAAB3...",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_import_host_key_viewer_cannot(self, viewer_client, device):
        """Test viewer cannot import host keys."""
        response = viewer_client.post(
            "/api/v1/ssh/host-keys/import/",
            data=json.dumps(
                {
                    "device_id": device.id,
                    "known_hosts_line": "192.168.1.1 ssh-rsa AAAAB3...",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSSHHostKeyAPIStats:
    """Tests for SSH host key statistics endpoint."""

    def test_get_stats(self, admin_client, host_key, admin_user):
        """Test getting host key statistics."""
        # Create some more keys
        from webnet.core.ssh_host_keys import SSHHostKeyService

        SSHHostKeyService.verify_key_manual(host_key, admin_user)

        SSHHostKey.objects.create(
            device=host_key.device,
            key_type=SSHHostKey.KEY_TYPE_ED25519,
            public_key="ssh-ed25519 AAAAC3...",
            fingerprint_sha256="xyz789",
        )

        response = admin_client.get("/api/v1/ssh/host-keys/stats/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["verified"] == 1
        assert data["unverified"] == 1
        assert "by_key_type" in data
        assert data["by_key_type"]["ssh-rsa"] == 1
        assert data["by_key_type"]["ssh-ed25519"] == 1

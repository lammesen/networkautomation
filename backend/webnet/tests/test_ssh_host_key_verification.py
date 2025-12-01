"""Tests for SSH host key verification and management."""

import base64
import hashlib
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from webnet.core.ssh_host_keys import (
    DatabaseKnownHostsCallback,
    HostKeyVerificationError,
    SSHHostKeyService,
)
from webnet.customers.models import Customer
from webnet.devices.models import Device, SSHHostKey


@pytest.fixture
def customer():
    """Create a test customer with TOFU policy."""
    return Customer.objects.create(
        name="Test Customer", ssh_host_key_policy=Customer.SSH_POLICY_TOFU
    )


@pytest.fixture
def strict_customer():
    """Create a test customer with strict policy."""
    return Customer.objects.create(
        name="Strict Customer", ssh_host_key_policy=Customer.SSH_POLICY_STRICT
    )


@pytest.fixture
def disabled_customer():
    """Create a test customer with disabled policy."""
    return Customer.objects.create(
        name="Disabled Customer", ssh_host_key_policy=Customer.SSH_POLICY_DISABLED
    )


@pytest.fixture
def credential(customer):
    """Create a test credential."""
    from webnet.devices.models import Credential

    cred = Credential.objects.create(
        customer=customer, name="test-cred", username="admin"
    )
    cred.password = "password123"
    cred.save()
    return cred


@pytest.fixture
def device(customer, credential):
    """Create a test device."""
    return Device.objects.create(
        customer=customer,
        hostname="test-device",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
    )


@pytest.fixture
def mock_ssh_key():
    """Create a mock SSH public key."""
    key = MagicMock()
    key.algorithm = "ssh-rsa"
    # Create a consistent key for testing
    key_data = b"AAAAB3NzaC1yc2EAAAADAQABAAABAQDtest"
    key_b64 = base64.b64encode(key_data).decode("ascii")
    key.export_public_key.return_value = f"ssh-rsa {key_b64}"
    return key


@pytest.fixture
def different_mock_ssh_key():
    """Create a different mock SSH public key."""
    key = MagicMock()
    key.algorithm = "ssh-rsa"
    # Different key data
    key_data = b"AAAAB3NzaC1yc2EAAAADAQABAAABAQDdifferent"
    key_b64 = base64.b64encode(key_data).decode("ascii")
    key.export_public_key.return_value = f"ssh-rsa {key_b64}"
    return key


@pytest.mark.django_db
class TestSSHHostKeyService:
    """Tests for SSHHostKeyService."""

    def test_compute_fingerprint(self, mock_ssh_key):
        """Test computing SSH key fingerprint."""
        fingerprint = SSHHostKeyService.compute_fingerprint(mock_ssh_key)
        assert fingerprint
        assert isinstance(fingerprint, str)
        # Fingerprint should be base64 without padding
        assert "=" not in fingerprint

    def test_get_key_type(self, mock_ssh_key):
        """Test getting key type."""
        key_type = SSHHostKeyService.get_key_type(mock_ssh_key)
        assert key_type == "ssh-rsa"

    def test_get_or_create_host_key_creates_new(self, device, mock_ssh_key):
        """Test creating a new host key."""
        assert SSHHostKey.objects.count() == 0

        host_key, created = SSHHostKeyService.get_or_create_host_key(
            device, mock_ssh_key
        )

        assert created
        assert host_key.device == device
        assert host_key.key_type == "ssh-rsa"
        assert host_key.fingerprint_sha256
        assert not host_key.verified
        assert SSHHostKey.objects.count() == 1

    def test_get_or_create_host_key_gets_existing(self, device, mock_ssh_key):
        """Test getting an existing host key."""
        # Create first time
        host_key1, created1 = SSHHostKeyService.get_or_create_host_key(
            device, mock_ssh_key
        )
        assert created1
        first_seen = host_key1.first_seen_at

        # Get second time
        host_key2, created2 = SSHHostKeyService.get_or_create_host_key(
            device, mock_ssh_key
        )
        assert not created2
        assert host_key2.id == host_key1.id
        assert host_key2.first_seen_at == first_seen
        assert host_key2.last_seen_at > first_seen
        assert SSHHostKey.objects.count() == 1

    def test_verify_host_key_disabled_policy(self, disabled_customer, device, mock_ssh_key):
        """Test that disabled policy accepts any key."""
        device.customer = disabled_customer
        device.save()

        result = SSHHostKeyService.verify_host_key(device, mock_ssh_key)
        assert result is True
        # No key should be stored with disabled policy
        assert SSHHostKey.objects.count() == 0

    def test_verify_host_key_tofu_first_connection(
        self, customer, device, mock_ssh_key
    ):
        """Test TOFU policy on first connection stores key."""
        result = SSHHostKeyService.verify_host_key(device, mock_ssh_key)
        assert result is True
        assert SSHHostKey.objects.count() == 1

        host_key = SSHHostKey.objects.first()
        assert host_key.device == device
        assert not host_key.verified

    def test_verify_host_key_tofu_matching_key(self, customer, device, mock_ssh_key):
        """Test TOFU policy accepts matching key."""
        # First connection - store key
        SSHHostKeyService.verify_host_key(device, mock_ssh_key)

        # Second connection with same key
        result = SSHHostKeyService.verify_host_key(device, mock_ssh_key)
        assert result is True
        assert SSHHostKey.objects.count() == 1

    def test_verify_host_key_tofu_changed_key(
        self, customer, device, mock_ssh_key, different_mock_ssh_key
    ):
        """Test TOFU policy warns but accepts changed key."""
        # First connection - store key
        SSHHostKeyService.verify_host_key(device, mock_ssh_key)
        assert SSHHostKey.objects.count() == 1

        # Second connection with different key
        result = SSHHostKeyService.verify_host_key(device, different_mock_ssh_key)
        assert result is True  # TOFU accepts changed keys
        # Both keys should be stored
        assert SSHHostKey.objects.count() == 2

    def test_verify_host_key_strict_first_connection(
        self, strict_customer, device, mock_ssh_key
    ):
        """Test strict policy rejects unknown keys."""
        device.customer = strict_customer
        device.save()

        with pytest.raises(HostKeyVerificationError) as exc_info:
            SSHHostKeyService.verify_host_key(device, mock_ssh_key)

        assert "strict mode" in str(exc_info.value).lower()
        assert SSHHostKey.objects.count() == 0

    def test_verify_host_key_strict_matching_key(
        self, strict_customer, device, mock_ssh_key
    ):
        """Test strict policy accepts known keys."""
        device.customer = strict_customer
        device.save()

        # Manually add the key first
        SSHHostKeyService.get_or_create_host_key(device, mock_ssh_key)

        # Should accept the known key
        result = SSHHostKeyService.verify_host_key(device, mock_ssh_key)
        assert result is True

    def test_verify_host_key_strict_changed_key(
        self, strict_customer, device, mock_ssh_key, different_mock_ssh_key
    ):
        """Test strict policy rejects changed keys."""
        device.customer = strict_customer
        device.save()

        # Manually add first key
        SSHHostKeyService.get_or_create_host_key(device, mock_ssh_key)

        # Try to connect with different key
        with pytest.raises(HostKeyVerificationError) as exc_info:
            SSHHostKeyService.verify_host_key(device, different_mock_ssh_key)

        assert "host key has changed" in str(exc_info.value).lower()
        assert SSHHostKey.objects.count() == 1  # Old key remains

    def test_verify_key_manual(self, device, mock_ssh_key, admin_user):
        """Test manually verifying a host key."""
        host_key, _ = SSHHostKeyService.get_or_create_host_key(device, mock_ssh_key)
        assert not host_key.verified

        SSHHostKeyService.verify_key_manual(host_key, admin_user)

        host_key.refresh_from_db()
        assert host_key.verified
        assert host_key.verified_by == admin_user
        assert host_key.verified_at is not None

    def test_unverify_key(self, device, mock_ssh_key, admin_user):
        """Test unverifying a host key."""
        host_key, _ = SSHHostKeyService.get_or_create_host_key(device, mock_ssh_key)
        SSHHostKeyService.verify_key_manual(host_key, admin_user)
        assert host_key.verified

        SSHHostKeyService.unverify_key(host_key)

        host_key.refresh_from_db()
        assert not host_key.verified
        assert host_key.verified_by is None
        assert host_key.verified_at is None

    def test_import_from_openssh_known_hosts(self, device):
        """Test importing a key from known_hosts format."""
        # Valid base64-encoded RSA key (with proper padding)
        known_hosts_line = (
            "192.168.1.1 ssh-rsa "
            "AAAAB3NzaC1yc2EAAAADAQABAAABAQDexamplekeydata123456789=="
        )

        host_key = SSHHostKeyService.import_from_openssh_known_hosts(
            device, known_hosts_line
        )

        assert host_key.device == device
        assert host_key.key_type == "ssh-rsa"
        assert host_key.fingerprint_sha256
        assert not host_key.verified

    def test_import_from_openssh_known_hosts_invalid_format(self, device):
        """Test importing invalid known_hosts line."""
        with pytest.raises(ValueError):
            SSHHostKeyService.import_from_openssh_known_hosts(device, "invalid")

    def test_import_from_openssh_known_hosts_duplicate(self, device):
        """Test importing duplicate key returns existing."""
        known_hosts_line = (
            "192.168.1.1 ssh-rsa "
            "AAAAB3NzaC1yc2EAAAADAQABAAABAQDexamplekeydata123456789=="
        )

        host_key1 = SSHHostKeyService.import_from_openssh_known_hosts(
            device, known_hosts_line
        )
        host_key2 = SSHHostKeyService.import_from_openssh_known_hosts(
            device, known_hosts_line
        )

        assert host_key1.id == host_key2.id
        assert SSHHostKey.objects.count() == 1


@pytest.mark.django_db
class TestDatabaseKnownHostsCallback:
    """Tests for DatabaseKnownHostsCallback."""

    def test_validate_host_public_key_accepts_valid(
        self, customer, device, mock_ssh_key
    ):
        """Test callback accepts valid key in TOFU mode."""
        callback = DatabaseKnownHostsCallback(device)
        result = callback.validate_host_public_key(
            "test-device", "192.168.1.1", 22, mock_ssh_key
        )
        assert result is True
        assert SSHHostKey.objects.count() == 1

    def test_validate_host_public_key_rejects_invalid_strict(
        self, strict_customer, device, mock_ssh_key
    ):
        """Test callback rejects unknown key in strict mode."""
        device.customer = strict_customer
        device.save()

        callback = DatabaseKnownHostsCallback(device)
        result = callback.validate_host_public_key(
            "test-device", "192.168.1.1", 22, mock_ssh_key
        )
        assert result is False
        assert SSHHostKey.objects.count() == 0

    def test_validate_host_public_key_exception_handling(self, device):
        """Test callback handles exceptions gracefully."""
        callback = DatabaseKnownHostsCallback(device)

        # Pass invalid key that will cause an exception
        invalid_key = MagicMock()
        invalid_key.export_public_key.side_effect = Exception("Test error")

        result = callback.validate_host_public_key(
            "test-device", "192.168.1.1", 22, invalid_key
        )
        assert result is False


@pytest.mark.django_db
class TestSSHHostKeyModel:
    """Tests for SSHHostKey model."""

    def test_create_ssh_host_key(self, device):
        """Test creating an SSH host key."""
        host_key = SSHHostKey.objects.create(
            device=device,
            key_type=SSHHostKey.KEY_TYPE_RSA,
            public_key="ssh-rsa AAAAB3NzaC1yc2EA...",
            fingerprint_sha256="abcd1234",
        )
        assert host_key.device == device
        assert host_key.key_type == SSHHostKey.KEY_TYPE_RSA
        assert not host_key.verified

    def test_fingerprint_display_property(self, device):
        """Test fingerprint_display property."""
        host_key = SSHHostKey.objects.create(
            device=device,
            key_type=SSHHostKey.KEY_TYPE_RSA,
            public_key="ssh-rsa AAAAB3NzaC1yc2EA...",
            fingerprint_sha256="abcd1234",
        )
        assert host_key.fingerprint_display == "SHA256:abcd1234"

    def test_unique_together_constraint(self, device):
        """Test unique constraint on device, key_type, fingerprint."""
        SSHHostKey.objects.create(
            device=device,
            key_type=SSHHostKey.KEY_TYPE_RSA,
            public_key="ssh-rsa AAAAB3NzaC1yc2EA...",
            fingerprint_sha256="abcd1234",
        )

        # Creating duplicate should raise error
        with pytest.raises(Exception):  # IntegrityError
            SSHHostKey.objects.create(
                device=device,
                key_type=SSHHostKey.KEY_TYPE_RSA,
                public_key="ssh-rsa AAAAB3NzaC1yc2EA...",
                fingerprint_sha256="abcd1234",
            )


@pytest.mark.django_db
class TestCustomerSSHPolicy:
    """Tests for Customer SSH policy field."""

    def test_customer_default_policy(self):
        """Test customer has default TOFU policy."""
        customer = Customer.objects.create(name="Test Customer")
        assert customer.ssh_host_key_policy == Customer.SSH_POLICY_TOFU

    def test_customer_policy_choices(self):
        """Test all policy choices can be set."""
        customer = Customer.objects.create(
            name="Test Customer", ssh_host_key_policy=Customer.SSH_POLICY_STRICT
        )
        assert customer.ssh_host_key_policy == Customer.SSH_POLICY_STRICT

        customer.ssh_host_key_policy = Customer.SSH_POLICY_DISABLED
        customer.save()
        customer.refresh_from_db()
        assert customer.ssh_host_key_policy == Customer.SSH_POLICY_DISABLED

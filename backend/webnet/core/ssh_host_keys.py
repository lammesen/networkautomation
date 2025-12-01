"""SSH host key verification and management service.

Implements database-backed host key storage with TOFU (Trust On First Use)
and strict verification policies to prevent MITM attacks.
"""

from __future__ import annotations

import asyncssh
import base64
import hashlib
import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from webnet.customers.models import Customer

if TYPE_CHECKING:
    from webnet.devices.models import Device, SSHHostKey
    from webnet.users.models import User

logger = logging.getLogger(__name__)


class HostKeyVerificationError(Exception):
    """Raised when host key verification fails."""

    pass


class SSHHostKeyService:
    """Service for managing SSH host key verification."""

    @staticmethod
    def compute_fingerprint(key: asyncssh.SSHKey) -> str:
        """Compute SHA256 fingerprint of SSH public key.

        Args:
            key: AsyncSSH public key object

        Returns:
            Base64-encoded SHA256 hash of the public key
        """
        key_data = key.export_public_key("openssh")
        # Remove the key type prefix and decode base64
        parts = key_data.split()
        if len(parts) >= 2:
            key_b64 = parts[1]
            key_bytes = base64.b64decode(key_b64)
            digest = hashlib.sha256(key_bytes).digest()
            return base64.b64encode(digest).decode("ascii").rstrip("=")
        raise ValueError("Invalid SSH key format")

    @staticmethod
    def get_key_type(key: asyncssh.SSHKey) -> str:
        """Get the key type/algorithm name.

        Args:
            key: AsyncSSH public key object

        Returns:
            Key type string (e.g., 'ssh-rsa', 'ssh-ed25519')
        """
        return key.algorithm

    @staticmethod
    def get_or_create_host_key(device: Device, key: asyncssh.SSHKey) -> tuple[SSHHostKey, bool]:
        """Get existing or create new host key record.

        Args:
            device: Device instance
            key: AsyncSSH public key object

        Returns:
            Tuple of (SSHHostKey instance, created boolean)
        """
        from webnet.devices.models import SSHHostKey

        key_type = SSHHostKeyService.get_key_type(key)
        fingerprint = SSHHostKeyService.compute_fingerprint(key)
        public_key_data = key.export_public_key("openssh")

        # Try to get existing key
        host_key = SSHHostKey.objects.filter(
            device=device, key_type=key_type, fingerprint_sha256=fingerprint
        ).first()

        if host_key:
            # Update last_seen_at
            host_key.last_seen_at = timezone.now()
            host_key.save(update_fields=["last_seen_at"])
            return host_key, False

        # Create new key
        host_key = SSHHostKey.objects.create(
            device=device,
            key_type=key_type,
            public_key=public_key_data,
            fingerprint_sha256=fingerprint,
        )
        return host_key, True

    @staticmethod
    def verify_host_key(device: Device, key: asyncssh.SSHKey) -> bool:
        """Verify SSH host key according to customer policy.

        Args:
            device: Device being connected to
            key: SSH public key received from host

        Returns:
            True if key is trusted/accepted, False otherwise

        Raises:
            HostKeyVerificationError: If key verification fails in strict mode
        """
        from webnet.devices.models import SSHHostKey

        customer = device.customer
        policy = customer.ssh_host_key_policy
        key_type = SSHHostKeyService.get_key_type(key)
        fingerprint = SSHHostKeyService.compute_fingerprint(key)

        logger.info(
            "Verifying SSH host key for device %s (policy: %s, key_type: %s)",
            device.hostname,
            policy,
            key_type,
        )

        # Policy: disabled - always accept
        if policy == Customer.SSH_POLICY_DISABLED:
            logger.warning(
                "SSH host key verification disabled for customer %s - accepting key",
                customer.name,
            )
            return True

        # Check if we have any keys for this device
        existing_keys = SSHHostKey.objects.filter(device=device, key_type=key_type).order_by(
            "-verified", "-first_seen_at"
        )

        if not existing_keys.exists():
            # No existing keys - TOFU (Trust On First Use)
            logger.info("No existing keys for device %s - applying TOFU policy", device.hostname)

            if policy == Customer.SSH_POLICY_STRICT:
                # Strict mode: reject unknown keys
                raise HostKeyVerificationError(
                    f"No known host key for {device.hostname}. "
                    f"In strict mode, unknown keys are rejected. "
                    f"Add the key manually or switch to TOFU mode."
                )

            # TOFU mode: accept and store first key
            logger.info("TOFU: Accepting and storing first key for %s", device.hostname)
            with transaction.atomic():
                SSHHostKeyService.get_or_create_host_key(device, key)
            return True

        # Check if the presented key matches any known key
        matching_key = existing_keys.filter(fingerprint_sha256=fingerprint).first()

        if matching_key:
            # Key matches - update last_seen and accept
            logger.info(
                "Host key matches known key for %s (verified=%s)",
                device.hostname,
                matching_key.verified,
            )
            matching_key.last_seen_at = timezone.now()
            matching_key.save(update_fields=["last_seen_at"])
            return True

        # Key mismatch - different key than what we have stored
        logger.warning(
            "Host key mismatch for device %s! Expected key type %s, got fingerprint %s",
            device.hostname,
            key_type,
            fingerprint,
        )

        if policy == Customer.SSH_POLICY_STRICT:
            # Strict mode: reject changed keys
            raise HostKeyVerificationError(
                f"Host key verification failed for {device.hostname}. "
                f"The host key has changed! This could indicate a man-in-the-middle attack. "
                f"Known fingerprints: {[k.fingerprint_sha256 for k in existing_keys[:3]]} "
                f"Received fingerprint: {fingerprint}"
            )

        # TOFU mode: warn but accept (store as new key)
        logger.warning(
            "TOFU: Host key changed for %s - storing new key but accepting connection",
            device.hostname,
        )
        with transaction.atomic():
            SSHHostKeyService.get_or_create_host_key(device, key)
        return True

    @staticmethod
    def verify_key_manual(host_key: SSHHostKey, user: User) -> None:
        """Manually verify a host key.

        Args:
            host_key: SSHHostKey instance to verify
            user: User performing the verification
        """
        host_key.verified = True
        host_key.verified_by = user
        host_key.verified_at = timezone.now()
        host_key.save(update_fields=["verified", "verified_by", "verified_at"])
        logger.info(
            "Host key manually verified for device %s by user %s",
            host_key.device.hostname,
            user.username,
        )

    @staticmethod
    def unverify_key(host_key: SSHHostKey) -> None:
        """Unverify a host key.

        Args:
            host_key: SSHHostKey instance to unverify
        """
        host_key.verified = False
        host_key.verified_by = None
        host_key.verified_at = None
        host_key.save(update_fields=["verified", "verified_by", "verified_at"])
        logger.info("Host key unverified for device %s", host_key.device.hostname)

    @staticmethod
    def import_from_openssh_known_hosts(device: Device, known_hosts_line: str) -> SSHHostKey:
        """Import a host key from OpenSSH known_hosts format.

        Args:
            device: Device to associate the key with
            known_hosts_line: Line from known_hosts file

        Returns:
            Created SSHHostKey instance

        Raises:
            ValueError: If the line cannot be parsed
        """
        parts = known_hosts_line.strip().split()
        if len(parts) < 3:
            raise ValueError("Invalid known_hosts line format")

        # Format: hostname key_type key_data [comment]
        # We ignore the hostname from the file and use the device's mgmt_ip
        key_type = parts[1]
        key_data_b64 = parts[2]

        # Decode and compute fingerprint
        key_data = base64.b64decode(key_data_b64)
        digest = hashlib.sha256(key_data).digest()
        fingerprint = base64.b64encode(digest).decode("ascii").rstrip("=")

        # Create public key string in OpenSSH format
        public_key = f"{key_type} {key_data_b64}"

        from webnet.devices.models import SSHHostKey

        # Check for existing key
        existing = SSHHostKey.objects.filter(
            device=device, key_type=key_type, fingerprint_sha256=fingerprint
        ).first()

        if existing:
            return existing

        # Create new key
        host_key = SSHHostKey.objects.create(
            device=device,
            key_type=key_type,
            public_key=public_key,
            fingerprint_sha256=fingerprint,
        )
        logger.info("Imported host key for device %s from known_hosts", device.hostname)
        return host_key


class DatabaseKnownHostsCallback:
    """AsyncSSH callback for database-backed host key verification."""

    def __init__(self, device: Device):
        """Initialize callback with device context.

        Args:
            device: Device being connected to
        """
        self.device = device

    def validate_host_public_key(
        self, host: str, addr: str, port: int, key: asyncssh.SSHKey
    ) -> bool:
        """Callback invoked by asyncssh when host key needs validation.

        Args:
            host: Hostname being connected to
            addr: IP address being connected to
            port: Port number
            key: SSH public key to validate

        Returns:
            True if key should be accepted, False otherwise
        """
        try:
            return SSHHostKeyService.verify_host_key(self.device, key)
        except HostKeyVerificationError as e:
            logger.error("Host key verification failed: %s", e)
            return False
        except Exception as e:
            logger.exception("Unexpected error during host key verification: %s", e)
            return False

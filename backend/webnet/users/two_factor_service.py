"""Two-factor authentication service for managing TOTP and backup codes."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from django.contrib.auth.hashers import check_password, make_password
from django_otp.plugins.otp_totp.models import TOTPDevice

if TYPE_CHECKING:
    from webnet.users.models import User


class TwoFactorService:
    """Service for managing two-factor authentication."""

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate a list of backup codes."""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            codes.append(code)
        return codes

    @staticmethod
    def hash_backup_codes(codes: list[str]) -> list[str]:
        """Hash backup codes for storage."""
        return [make_password(code) for code in codes]

    @staticmethod
    def verify_backup_code(user: User, code: str) -> bool:
        """Verify a backup code and mark it as used."""
        if not user.backup_codes:
            return False

        code = code.upper().strip()
        for i, hashed_code in enumerate(user.backup_codes):
            if check_password(code, hashed_code):
                # Remove the used code
                user.backup_codes.pop(i)
                user.save(update_fields=["backup_codes"])
                return True
        return False

    @staticmethod
    def enable_totp_for_user(user: User, device_name: str = "default") -> TOTPDevice:
        """Enable TOTP device for user."""
        # Only delete unconfirmed devices to prevent accidental deletion of confirmed 2FA
        TOTPDevice.objects.filter(user=user, name=device_name, confirmed=False).delete()

        # Create new device
        device = TOTPDevice.objects.create(
            user=user,
            name=device_name,
            confirmed=False,
        )
        return device

    @staticmethod
    def confirm_totp_device(device: TOTPDevice, token: str) -> bool:
        """Confirm TOTP device with a valid token."""
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            # Update user's 2FA status
            user = device.user
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_enabled"])
            return True
        return False

    @staticmethod
    def disable_2fa_for_user(user: User) -> None:
        """Disable 2FA for user."""
        # Delete all TOTP devices
        TOTPDevice.objects.filter(user=user).delete()

        # Clear backup codes and disable 2FA
        user.two_factor_enabled = False
        user.backup_codes = []
        user.save(update_fields=["two_factor_enabled", "backup_codes"])

    @staticmethod
    def get_totp_device(user: User) -> TOTPDevice | None:
        """Get user's confirmed TOTP device."""
        try:
            return TOTPDevice.objects.get(user=user, confirmed=True)
        except TOTPDevice.DoesNotExist:
            return None

    @staticmethod
    def verify_totp_token(user: User, token: str) -> bool:
        """Verify TOTP token for user."""
        device = TwoFactorService.get_totp_device(user)
        if device and device.verify_token(token):
            return True
        return False

    @staticmethod
    def regenerate_backup_codes(user: User) -> list[str]:
        """Regenerate backup codes for user."""
        codes = TwoFactorService.generate_backup_codes()
        hashed_codes = TwoFactorService.hash_backup_codes(codes)
        user.backup_codes = hashed_codes
        user.save(update_fields=["backup_codes"])
        return codes

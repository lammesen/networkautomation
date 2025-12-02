"""Tests for two-factor authentication functionality."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from webnet.users.two_factor_service import TwoFactorService

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        role="operator",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin test user."""
    return User.objects.create_user(
        username="adminuser",
        password="adminpass123",
        role="admin",
    )


@pytest.fixture
def client_logged_in(client: Client, user: User):
    """Client with logged in user."""
    client.login(username="testuser", password="testpass123")
    return client


class TestTwoFactorService:
    """Test two-factor authentication service."""

    def test_generate_backup_codes(self):
        """Test backup code generation."""
        codes = TwoFactorService.generate_backup_codes(count=10)
        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        # Check all codes are unique
        assert len(set(codes)) == 10

    def test_hash_backup_codes(self):
        """Test backup code hashing."""
        codes = ["12345678", "ABCDEF12"]
        hashed = TwoFactorService.hash_backup_codes(codes)
        assert len(hashed) == 2
        # Hashed codes should be different from originals
        assert hashed[0] != codes[0]
        assert hashed[1] != codes[1]

    def test_verify_backup_code(self, user: User):
        """Test backup code verification."""
        codes = TwoFactorService.generate_backup_codes(count=3)
        hashed = TwoFactorService.hash_backup_codes(codes)
        user.backup_codes = hashed
        user.save()

        # Verify first code
        assert TwoFactorService.verify_backup_code(user, codes[0])
        # Code should be removed after use
        user.refresh_from_db()
        assert len(user.backup_codes) == 2

        # Verify same code again should fail
        assert not TwoFactorService.verify_backup_code(user, codes[0])

        # Invalid code should fail
        assert not TwoFactorService.verify_backup_code(user, "INVALID1")

    def test_enable_totp_for_user(self, user: User):
        """Test TOTP device creation."""
        device = TwoFactorService.enable_totp_for_user(user)
        assert device.user == user
        assert device.name == "default"
        assert not device.confirmed

    def test_confirm_totp_device(self, user: User):
        """Test TOTP device confirmation."""
        device = TwoFactorService.enable_totp_for_user(user)

        # Generate a valid token
        token = device.token()

        # Confirm device with valid token
        assert TwoFactorService.confirm_totp_device(device, token)
        device.refresh_from_db()
        assert device.confirmed

        # Check user's 2FA status
        user.refresh_from_db()
        assert user.two_factor_enabled

    def test_confirm_totp_device_invalid_token(self, user: User):
        """Test TOTP device confirmation with invalid token."""
        device = TwoFactorService.enable_totp_for_user(user)

        # Try with invalid token
        assert not TwoFactorService.confirm_totp_device(device, "123456")
        device.refresh_from_db()
        assert not device.confirmed

    def test_disable_2fa_for_user(self, user: User):
        """Test disabling 2FA."""
        # Enable 2FA first
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Add backup codes
        codes = TwoFactorService.generate_backup_codes()
        hashed = TwoFactorService.hash_backup_codes(codes)
        user.backup_codes = hashed
        user.save()

        # Disable 2FA
        TwoFactorService.disable_2fa_for_user(user)

        # Check everything is disabled
        user.refresh_from_db()
        assert not user.two_factor_enabled
        assert user.backup_codes == []
        assert not TOTPDevice.objects.filter(user=user).exists()

    def test_get_totp_device(self, user: User):
        """Test getting TOTP device."""
        # No device initially
        assert TwoFactorService.get_totp_device(user) is None

        # Create unconfirmed device
        device = TwoFactorService.enable_totp_for_user(user)
        assert TwoFactorService.get_totp_device(user) is None

        # Confirm device
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Should return device now
        retrieved = TwoFactorService.get_totp_device(user)
        assert retrieved is not None
        assert retrieved.id == device.id

    def test_verify_totp_token(self, user: User):
        """Test TOTP token verification."""
        # Enable and confirm 2FA
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Generate and verify new token
        new_token = device.token()
        assert TwoFactorService.verify_totp_token(user, new_token)

        # Invalid token
        assert not TwoFactorService.verify_totp_token(user, "123456")

    def test_regenerate_backup_codes(self, user: User):
        """Test backup code regeneration."""
        # Generate initial codes
        initial_codes = TwoFactorService.regenerate_backup_codes(user)
        assert len(initial_codes) == 10
        user.refresh_from_db()
        assert len(user.backup_codes) == 10

        # Regenerate codes
        new_codes = TwoFactorService.regenerate_backup_codes(user)
        assert len(new_codes) == 10
        # New codes should be different
        assert set(initial_codes) != set(new_codes)
        user.refresh_from_db()
        assert len(user.backup_codes) == 10


class TestTwoFactorViews:
    """Test two-factor authentication views."""

    def test_2fa_setup_view_requires_login(self, client: Client):
        """Test 2FA setup requires authentication."""
        response = client.get(reverse("2fa-setup"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_2fa_setup_view_get(self, client_logged_in: Client):
        """Test 2FA setup GET request."""
        response = client_logged_in.get(reverse("2fa-setup"))
        assert response.status_code == 200
        assert "qr_url" in response.context
        assert "secret" in response.context

    def test_2fa_manage_view_requires_login(self, client: Client):
        """Test 2FA manage requires authentication."""
        response = client.get(reverse("2fa-manage"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_2fa_manage_view_get(self, client_logged_in: Client):
        """Test 2FA manage GET request."""
        response = client_logged_in.get(reverse("2fa-manage"))
        assert response.status_code == 200
        assert "two_factor_enabled" in response.context

    def test_2fa_disable_requires_login(self, client: Client):
        """Test 2FA disable requires authentication."""
        response = client.post(reverse("2fa-disable"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_2fa_disable_when_not_required(self, client_logged_in: Client, user: User):
        """Test disabling 2FA when not required."""
        # Enable 2FA first
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Disable it
        response = client_logged_in.post(reverse("2fa-disable"))
        assert response.status_code == 302

        # Check it's disabled
        user.refresh_from_db()
        assert not user.two_factor_enabled

    def test_2fa_disable_when_required(self, client_logged_in: Client, user: User):
        """Test disabling 2FA when required fails."""
        # Enable 2FA and mark as required
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)
        user.two_factor_required = True
        user.save()

        # Try to disable it
        response = client_logged_in.post(reverse("2fa-disable"))
        assert response.status_code == 302

        # Check it's still enabled
        user.refresh_from_db()
        assert user.two_factor_enabled


class TestCustomLoginView:
    """Test custom login view with 2FA."""

    def test_login_without_2fa(self, client: Client, user: User):
        """Test login when 2FA is not enabled."""
        response = client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/"

    def test_login_with_2fa_redirects_to_verify(self, client: Client, user: User):
        """Test login with 2FA redirects to verification."""
        # Enable 2FA
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Try to login
        response = client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == reverse("2fa-verify")


class TestUserModel:
    """Test User model 2FA methods."""

    def test_has_backup_codes(self, user: User):
        """Test has_backup_codes method."""
        assert not user.has_backup_codes()

        user.backup_codes = ["hashed_code_1", "hashed_code_2"]
        user.save()
        assert user.has_backup_codes()

    def test_is_2fa_enabled(self, user: User):
        """Test is_2fa_enabled method."""
        assert not user.is_2fa_enabled()

        user.two_factor_enabled = True
        user.save()
        assert user.is_2fa_enabled()


class TestSecurityFixes:
    """Test security fixes for 2FA."""

    def test_open_redirect_prevention(self, client: Client, user: User):
        """Test that open redirect is prevented in 2FA verify."""
        # Enable 2FA
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Try to login with malicious next URL
        response = client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == reverse("2fa-verify")

        # Try to verify with malicious redirect
        new_token = device.token()
        response = client.post(
            reverse("2fa-verify") + "?next=https://evil-site.com",
            {"token": new_token},
        )

        # Should redirect to safe URL, not evil site
        assert response.status_code == 302
        assert "evil-site.com" not in response.url
        assert response.url == "/"

    def test_setup_page_with_confirmed_2fa(self, client_logged_in: Client, user: User):
        """Test that users with confirmed 2FA can't access setup page."""
        # Enable and confirm 2FA
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)

        # Try to access setup page
        response = client_logged_in.get(reverse("2fa-setup"))

        # Should redirect to manage page
        assert response.status_code == 302
        assert response.url == reverse("2fa-manage")

        # Verify device still exists and is confirmed
        device.refresh_from_db()
        assert device.confirmed
        user.refresh_from_db()
        assert user.two_factor_enabled

    def test_enable_totp_preserves_confirmed_devices(self, user: User):
        """Test that enable_totp_for_user doesn't delete confirmed devices."""
        # Create and confirm a device
        device = TwoFactorService.enable_totp_for_user(user)
        token = device.token()
        TwoFactorService.confirm_totp_device(device, token)
        confirmed_device_id = device.id

        # Try to enable again (should only delete unconfirmed)
        new_device = TwoFactorService.enable_totp_for_user(user)

        # Confirmed device should still exist
        assert TOTPDevice.objects.filter(id=confirmed_device_id, confirmed=True).exists()
        # New unconfirmed device should be created
        assert not new_device.confirmed
        assert new_device.id != confirmed_device_id

    def test_session_cycle_on_login(self, client: Client, user: User):
        """Test that session key is regenerated after password auth."""
        # Get initial session key
        client.get(reverse("login"))
        initial_session_key = client.session.session_key

        # Login
        client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass123"},
        )

        # Session key should be different after login
        new_session_key = client.session.session_key
        assert new_session_key != initial_session_key

"""Tests for crypto module."""

import pytest
from cryptography.fernet import InvalidToken

from app.core.crypto import decrypt_text, encrypt_text


class TestEncryptDecrypt:
    """Test encrypt/decrypt roundtrip."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt then decrypt returns original value."""
        original = "my_secret_password"
        encrypted = encrypt_text(original)

        assert encrypted is not None
        assert encrypted != original  # Encrypted should differ from original
        assert decrypt_text(encrypted) == original

    def test_encrypt_none_returns_none(self):
        """Test that encrypting None returns None."""
        assert encrypt_text(None) is None

    def test_decrypt_none_returns_none(self):
        """Test that decrypting None returns None."""
        assert decrypt_text(None) is None

    def test_decrypt_invalid_raises_exception(self):
        """Test that decrypting invalid ciphertext raises InvalidToken."""
        plaintext = "not_encrypted_value"
        with pytest.raises(InvalidToken):
            decrypt_text(plaintext)

    def test_encrypt_empty_string(self):
        """Test that encrypting empty string works."""
        encrypted = encrypt_text("")
        assert encrypted is not None
        assert decrypt_text(encrypted) == ""

    def test_encrypt_unicode(self):
        """Test that encrypting unicode strings works."""
        original = "password123!@#日本語"
        encrypted = encrypt_text(original)
        assert decrypt_text(encrypted) == original

    def test_encrypt_produces_different_ciphertext(self):
        """Test that encrypting same value twice produces different ciphertext (due to IV)."""
        original = "same_password"
        encrypted1 = encrypt_text(original)
        encrypted2 = encrypt_text(original)

        # Fernet uses random IV, so ciphertexts should differ
        assert encrypted1 != encrypted2
        # But both should decrypt to same value
        assert decrypt_text(encrypted1) == original
        assert decrypt_text(encrypted2) == original

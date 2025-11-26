"""Simple symmetric encryption helpers for credential storage."""

from __future__ import annotations

import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        try:
            _fernet = Fernet(settings.encryption_key)
        except Exception as exc:  # pragma: no cover - fail-fast
            raise RuntimeError("ENCRYPTION_KEY is invalid; expected base64 Fernet key") from exc
    return _fernet


def encrypt_text(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a plaintext string; returns None if input is None."""
    if plaintext is None:
        return None
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt text previously encrypted with encrypt_text.

    Raises InvalidToken if the ciphertext cannot be decrypted.
    """
    if ciphertext is None:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt ciphertext - invalid token or corrupted data")
        raise

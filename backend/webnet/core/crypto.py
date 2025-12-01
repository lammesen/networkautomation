"""Encryption utilities using Fernet.

Passwords/enable passwords are stored encrypted at rest. ENCRYPTION_KEY must be
provided via environment; raise loudly if missing/invalid to avoid silent
plaintext storage.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_fernet() -> Fernet:
    key = getattr(settings, "ENCRYPTION_KEY", None) or getattr(settings, "encryption_key", None)
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is required for credential encryption")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError("Invalid ENCRYPTION_KEY provided") from exc


def encrypt_text(value: str | None) -> str:
    if value is None:
        return ""
    f = _get_fernet()
    token = f.encrypt(value.encode())
    return token.decode()


def decrypt_text(value: str | None) -> str | None:
    if not value:
        return None
    f = _get_fernet()
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover - corruption or wrong key
        raise RuntimeError("Failed to decrypt secret with provided ENCRYPTION_KEY") from exc

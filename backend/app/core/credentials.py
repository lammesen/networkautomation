from __future__ import annotations

from typing import Optional, Tuple

import hvac
from sqlalchemy.orm import Session

from app.core.config import settings
from app.devices.models import Credential, Device


class CredentialResolutionError(Exception):
    """Raised when credentials cannot be resolved."""


def _vault_client() -> hvac.Client:
    if not settings.vault_addr or not settings.vault_token:
        raise CredentialResolutionError("Vault is not configured")
    client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
    if not client.is_authenticated():
        raise CredentialResolutionError("Vault authentication failed")
    return client


def _resolve_from_vault(secret_path: str) -> Tuple[str, str]:
    client = _vault_client()
    mount_point = settings.vault_kv_mount
    secret = client.secrets.kv.v2.read_secret_version(path=secret_path, mount_point=mount_point)
    data = secret.get("data", {}).get("data", {})
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise CredentialResolutionError("Vault secret missing username/password")
    return username, password


def resolve_credentials_for_device(db: Session | None, device: Device) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns username/password for the provided device, optionally resolving from Vault
    when ``secret_path`` is populated on the credential record.
    """

    if not device.credentials:
        return None, None
    credential: Credential = device.credentials
    if credential.secret_path:
        return _resolve_from_vault(credential.secret_path)
    return credential.username, credential.password

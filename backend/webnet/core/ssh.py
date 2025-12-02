"""SSH session manager wrapper (placeholder integrating asyncssh)."""

from __future__ import annotations

import asyncssh
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from webnet.devices.models import Device

logger = logging.getLogger(__name__)


@dataclass
class SSHResult:
    stdout: str
    stderr: str
    exit_status: int


def _decode_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _resolve_known_hosts() -> str | list[str] | None:
    strict_verify = getattr(settings, "SSH_STRICT_HOST_VERIFY", True)
    if not strict_verify:
        return None

    configured = getattr(settings, "SSH_KNOWN_HOSTS_PATH", None)
    if configured:
        path = Path(configured).expanduser()
        if not path.exists():
            if getattr(settings, "DEBUG", False):
                logger.warning("Known hosts file missing at %s; allowing in DEBUG", path)
                return None
            raise SSHSessionError(f"Known hosts file not found: {path}")
        return str(path)

    default_path = Path("~/.ssh/known_hosts").expanduser()
    if default_path.exists():
        return str(default_path)

    if getattr(settings, "DEBUG", False):
        logger.warning("SSH strict verification enabled but known_hosts missing; allowing in DEBUG")
        return None

    raise SSHSessionError(
        "SSH host verification enabled but no known_hosts file found; set SSH_KNOWN_HOSTS_PATH or "
        "explicitly disable via SSH_STRICT_HOST_VERIFY=false (not recommended)."
    )


class SSHSession:
    def __init__(self, connection: asyncssh.SSHClientConnection):
        self.conn = connection

    async def run_command(self, command: str) -> SSHResult:
        result = await self.conn.run(command)
        return SSHResult(
            stdout=_decode_text(getattr(result, "stdout", "")),
            stderr=_decode_text(getattr(result, "stderr", "")),
            exit_status=int(getattr(result, "exit_status", 0)),
        )

    async def close(self) -> None:
        self.conn.close()
        await self.conn.wait_closed()


class SSHSessionError(Exception):
    pass


class SSHSessionManager:
    async def open_session(
        self, host: str, port: int, username: str, password: str, device: Device | None = None
    ) -> SSHSession:
        """Open an SSH session with optional database-backed host key verification.

        Args:
            host: Hostname or IP to connect to
            port: SSH port
            username: SSH username
            password: SSH password
            device: Optional Device instance for database-backed host key verification.
                    If provided, uses customer's SSH policy. If None, falls back to file-based
                    known_hosts verification.

        Returns:
            SSHSession instance

        Raises:
            SSHSessionError: If connection fails or host key verification fails
        """
        try:
            # If device is provided, use database-backed verification
            if device is not None:
                from webnet.core.ssh_host_keys import DatabaseKnownHostsCallback

                callback = DatabaseKnownHostsCallback(device)
                # Use empty known_hosts to force validation callback
                conn = await asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=b"",  # Empty known_hosts forces callback validation
                    validate_host_public_key=callback.validate_host_public_key,
                )
            else:
                # Fallback to file-based known_hosts
                known_hosts = _resolve_known_hosts()
                conn = await asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=known_hosts,
                )
            return SSHSession(conn)
        except SSHSessionError:
            raise
        except asyncssh.Error as exc:  # pragma: no cover - network dependent
            logger.warning("SSH connection failed for %s:%s: %s", host, port, exc)
            raise SSHSessionError(str(exc))
        except Exception as exc:  # pragma: no cover - defensive catch-all
            logger.exception("Unexpected SSH error for %s:%s", host, port)
            raise SSHSessionError(str(exc))

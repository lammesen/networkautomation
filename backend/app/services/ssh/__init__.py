"""Public entrypoints for the SSH service."""

from functools import lru_cache

from app.core.config import settings

from .manager import SSHSessionConfig, SSHSessionManager

__all__ = ["SSHSessionConfig", "SSHSessionManager", "get_ssh_session_manager"]


@lru_cache(maxsize=1)
def get_ssh_session_manager() -> SSHSessionManager:
    """Provide a process-wide SSH session manager using app settings."""
    config = SSHSessionConfig(
        connect_timeout=settings.ssh_connect_timeout,
        command_timeout=settings.ssh_command_timeout,
        keepalive_interval=settings.ssh_keepalive_interval,
        max_sessions=settings.ssh_max_sessions,
    )
    return SSHSessionManager(config=config)


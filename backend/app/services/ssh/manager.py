"""Async SSH session management built on top of asyncSSH."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Optional

import asyncssh


class SSHSessionError(Exception):
    """Raised when establishing or using an SSH session fails."""


@dataclass(slots=True)
class SSHSessionConfig:
    """Runtime limits/tuning for SSH streaming."""

    connect_timeout: float = 10.0
    command_timeout: float = 60.0
    keepalive_interval: float = 30.0
    max_sessions: int = 32


@dataclass(slots=True)
class SSHCommandResult:
    """Structured result for a command executed over SSH."""

    command: str
    stdout: str
    stderr: str
    exit_status: int


class SSHSession:
    """Wraps an asyncssh connection with command helpers."""

    def __init__(
        self,
        session_id: str,
        connection: asyncssh.SSHClientConnection,
        manager: "SSHSessionManager",
        config: SSHSessionConfig,
    ) -> None:
        self.id = session_id
        self._conn = connection
        self._manager = manager
        self._config = config
        self._closed = asyncio.Event()
        self._command_lock = asyncio.Lock()

    async def run_command(self, command: str) -> SSHCommandResult:
        """Execute a command and return stdout/stderr."""
        async with self._command_lock:
            try:
                result = await asyncio.wait_for(
                    self._conn.run(command, check=False),
                    timeout=self._config.command_timeout,
                )
            except asyncio.TimeoutError as exc:
                raise SSHSessionError("SSH command timed out") from exc
            except asyncssh.Error as exc:
                raise SSHSessionError(str(exc)) from exc

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_status: int = getattr(result, "exit_status", 0) or 0
            return SSHCommandResult(
                command=command,
                stdout=stdout,
                stderr=stderr,
                exit_status=exit_status,
            )

    async def close(self) -> None:
        """Terminate the SSH connection."""
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self._conn.close()
            await self._conn.wait_closed()
        finally:
            await self._manager.release(self.id)


class SSHSessionManager:
    """Limits concurrent sessions and centralises connection creation."""

    def __init__(self, config: SSHSessionConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()
        self._sessions: dict[str, SSHSession] = {}

    async def open_session(
        self,
        *,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        session_id: Optional[str] = None,
    ) -> SSHSession:
        """Establish an SSH session with concurrency and timeout controls."""
        session_id = session_id or str(uuid.uuid4())
        async with self._lock:
            if len(self._sessions) >= self._config.max_sessions:
                raise SSHSessionError("Maximum number of SSH sessions reached")

        try:
            connection = await asyncio.wait_for(
                asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=None,
                    client_keys=None,
                    keepalive_interval=self._config.keepalive_interval,
                ),
                timeout=self._config.connect_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise SSHSessionError("SSH connection timed out") from exc
        except asyncssh.Error as exc:
            raise SSHSessionError(str(exc)) from exc

        session = SSHSession(session_id, connection, self, self._config)
        async with self._lock:
            self._sessions[session_id] = session
        return session

    async def release(self, session_id: str) -> None:
        """Remove a session from bookkeeping."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def close_all(self) -> None:
        """Best-effort close for use in cleanup/tests."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        await asyncio.gather(*(session.close() for session in sessions), return_exceptions=True)


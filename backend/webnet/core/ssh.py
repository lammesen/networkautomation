"""SSH session manager wrapper (placeholder integrating asyncssh)."""

from __future__ import annotations

import asyncssh
from dataclasses import dataclass


@dataclass
class SSHResult:
    stdout: str
    stderr: str
    exit_status: int


class SSHSession:
    def __init__(self, connection: asyncssh.SSHClientConnection):
        self.conn = connection

    async def run_command(self, command: str) -> SSHResult:
        result = await self.conn.run(command)
        return SSHResult(stdout=result.stdout, stderr=result.stderr, exit_status=result.exit_status)

    async def close(self) -> None:
        self.conn.close()
        await self.conn.wait_closed()


class SSHSessionError(Exception):
    pass


class SSHSessionManager:
    async def open_session(self, host: str, port: int, username: str, password: str):
        try:
            conn = await asyncssh.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
            )
            return SSHSession(conn)
        except Exception as exc:  # pragma: no cover - network dependent
            raise SSHSessionError(str(exc))

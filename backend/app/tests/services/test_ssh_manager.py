import asyncio
from types import SimpleNamespace

import pytest

from app.services.ssh.manager import (
    SSHSessionConfig,
    SSHSessionError,
    SSHSessionManager,
)


class DummyConnection:
    def __init__(self, run_impl):
        self._run_impl = run_impl
        self.closed = False

    async def run(self, command: str, check: bool = False):
        return await self._run_impl(command)

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return


@pytest.mark.asyncio
async def test_open_session_and_run_command(monkeypatch):
    async def fake_connect(**kwargs):
        async def run_impl(command: str):
            return SimpleNamespace(stdout=f"ran {command}", stderr="", exit_status=0)

        return DummyConnection(run_impl)

    monkeypatch.setattr("app.services.ssh.manager.asyncssh.connect", fake_connect)

    manager = SSHSessionManager(SSHSessionConfig(max_sessions=1))
    session = await manager.open_session(
        host="127.0.0.1",
        username="user",
        password="pass",
        session_id="test",
    )

    result = await session.run_command("show version")
    assert result.stdout == "ran show version"
    assert result.stderr == ""
    assert result.exit_status == 0
    await session.close()


@pytest.mark.asyncio
async def test_concurrent_session_limit(monkeypatch):
    async def fake_connect(**kwargs):
        async def run_impl(command: str):
            return SimpleNamespace(stdout="", stderr="", exit_status=0)

        return DummyConnection(run_impl)

    monkeypatch.setattr("app.services.ssh.manager.asyncssh.connect", fake_connect)

    manager = SSHSessionManager(SSHSessionConfig(max_sessions=1))
    session = await manager.open_session(
        host="10.0.0.1", username="user", password="pass", session_id="one"
    )

    with pytest.raises(SSHSessionError, match="Maximum number of SSH sessions"):
        await manager.open_session(
            host="10.0.0.1", username="user", password="pass", session_id="two"
        )

    await session.close()


@pytest.mark.asyncio
async def test_command_timeout(monkeypatch):
    async def fake_connect(**kwargs):
        async def run_impl(command: str):
            raise asyncio.TimeoutError()

        return DummyConnection(run_impl)

    monkeypatch.setattr("app.services.ssh.manager.asyncssh.connect", fake_connect)

    manager = SSHSessionManager(
        SSHSessionConfig(max_sessions=1, command_timeout=0.01)
    )
    session = await manager.open_session(
        host="10.0.0.1", username="user", password="pass", session_id="timeout"
    )

    with pytest.raises(SSHSessionError, match="SSH command timed out"):
        await session.run_command("show run")

    await session.close()


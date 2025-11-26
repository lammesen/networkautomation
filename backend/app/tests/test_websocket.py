import json
import os

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.auth import get_password_hash
from app.db.models import Device, Job, User
from app.dependencies import get_db, get_ssh_manager
from app.main import app
from app.services.ssh.manager import SSHCommandResult

DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin123!")


class FakeSession:
    def __init__(self):
        self.closed = False

    async def run_command(self, command: str) -> SSHCommandResult:
        return SSHCommandResult(
            command=command,
            stdout=f"output:{command}",
            stderr="",
            exit_status=0,
        )

    async def close(self) -> None:
        self.closed = True


class FakeManager:
    def __init__(self):
        self.sessions = []

    async def open_session(self, **kwargs):
        self.sessions.append(kwargs)
        return FakeSession()


def test_device_ssh_websocket_flow(db_session, admin_user, test_customer, test_credential):
    device = Device(
        hostname="dev1",
        mgmt_ip="127.0.0.1",
        vendor="linux",
        platform="linux",
        customer_id=test_customer.id,
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    def override_get_db():
        yield db_session

    fake_manager = FakeManager()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ssh_manager] = lambda: fake_manager

    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
            )
            token = login.json()["access_token"]
            url = f"/api/v1/ws/devices/{device.id}/ssh?token={token}&customer_id={test_customer.id}"
            with client.websocket_connect(url) as websocket:
                connected = websocket.receive_json()
                assert connected["type"] == "connected"
                websocket.send_text(json.dumps({"type": "command", "command": "show"}))
                ack = websocket.receive_json()
                assert ack["type"] == "command_ack"
                output = websocket.receive_json()
                assert output["type"] == "output"
                assert output["stdout"] == "output:show"
    finally:
        app.dependency_overrides.clear()


def test_job_log_websocket_enforces_customer_scope(db_session, test_customer, second_customer):
    """Users from other customers should not read job logs."""
    # Create a job for the first customer
    job = Job(
        type="run_commands",
        status="queued",
        user_id=1,
        customer_id=test_customer.id,
    )
    db_session.add(job)

    # Create an unrelated user in a different customer
    outsider = User(
        username="outsider",
        hashed_password=get_password_hash("Outsider123!"),
        role="viewer",
        is_active=True,
    )
    outsider.customers.append(second_customer)
    db_session.add(outsider)
    db_session.commit()
    db_session.refresh(job)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"username": "outsider", "password": "Outsider123!"},
            )
            token = login.json()["access_token"]
            url = f"/api/v1/ws/jobs/{job.id}?token={token}"
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with client.websocket_connect(url) as websocket:
                    websocket.receive_json()
            assert excinfo.value.code == 1008
    finally:
        app.dependency_overrides.clear()

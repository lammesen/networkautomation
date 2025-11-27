"""Tests for commands API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestCommandSuggestions:
    """Tests for command suggestions endpoint."""

    def test_suggestions_requires_auth(self, client):
        """Test that suggestions require authentication."""
        response = client.get("/api/v1/commands/suggestions?platform=ios")
        assert response.status_code == 401

    def test_suggestions_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot access suggestions (operator-only)."""
        response = client.get("/api/v1/commands/suggestions?platform=ios", headers=viewer_headers)
        assert response.status_code == 403

    def test_suggestions_ios(self, client, operator_headers):
        """Test getting IOS command suggestions."""
        response = client.get("/api/v1/commands/suggestions?platform=ios", headers=operator_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "show version" in data
        assert "show ip interface brief" in data
        assert "show running-config" in data

    def test_suggestions_nxos(self, client, operator_headers):
        """Test getting NX-OS command suggestions."""
        response = client.get(
            "/api/v1/commands/suggestions?platform=nxos", headers=operator_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "show version" in data
        assert "show port-channel summary" in data

    def test_suggestions_eos(self, client, operator_headers):
        """Test getting Arista EOS command suggestions."""
        response = client.get("/api/v1/commands/suggestions?platform=eos", headers=operator_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "show version" in data
        assert "show lldp neighbors" in data

    def test_suggestions_junos(self, client, operator_headers):
        """Test getting Junos command suggestions."""
        response = client.get(
            "/api/v1/commands/suggestions?platform=junos", headers=operator_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "show version" in data
        assert "show configuration" in data

    def test_suggestions_unknown_platform(self, client, operator_headers):
        """Test getting suggestions for unknown platform returns empty list."""
        response = client.get(
            "/api/v1/commands/suggestions?platform=unknown", headers=operator_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_suggestions_case_insensitive(self, client, operator_headers):
        """Test that platform matching is case-insensitive."""
        response = client.get("/api/v1/commands/suggestions?platform=IOS", headers=operator_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "show version" in data

    def test_suggestions_missing_platform(self, client, operator_headers):
        """Test that platform parameter is required."""
        response = client.get("/api/v1/commands/suggestions", headers=operator_headers)
        assert response.status_code == 422


class TestRunCommands:
    """Tests for run commands endpoint."""

    def test_run_commands_requires_auth(self, client):
        """Test that running commands requires authentication."""
        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show version"],
            },
        )
        assert response.status_code == 401

    def test_run_commands_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot run commands."""
        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show version"],
            },
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_operator_success(
        self, mock_send_task, client, operator_headers, db_session
    ):
        """Test that operators can run commands."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show version", "show interfaces"],
            },
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_admin_success(self, mock_send_task, client, auth_headers, db_session):
        """Test that admins can run commands."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"vendors": ["cisco"]},
                "commands": ["show version"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 202
        assert "job_id" in response.json()

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_with_timeout(self, mock_send_task, client, operator_headers, db_session):
        """Test running commands with custom timeout."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show tech-support"],
                "timeout_sec": 300,
            },
            headers=operator_headers,
        )

        assert response.status_code == 202

        # Verify timeout was passed to celery task
        call_args = mock_send_task.call_args
        assert call_args[1]["args"][3] == 300  # timeout_sec

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_creates_job(
        self, mock_send_task, client, operator_headers, db_session, test_customer
    ):
        """Test that running commands creates a job record."""
        from app.db.models import Job

        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1", "router2"]},
                "commands": ["show version"],
            },
            headers=operator_headers,
        )

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Verify job was created
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.type == "run_commands"
        assert job.customer_id == test_customer.id
        assert job.payload_json["commands"] == ["show version"]

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_scheduled(self, mock_send_task, client, operator_headers, db_session):
        """Test scheduling commands for future execution."""
        mock_send_task.return_value = MagicMock()
        future_time = datetime.utcnow() + timedelta(hours=1)

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show version"],
                "execute_at": future_time.isoformat(),
            },
            headers=operator_headers,
        )

        assert response.status_code == 202

        # Verify task was scheduled with eta
        call_args = mock_send_task.call_args
        assert call_args[1].get("eta") is not None

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_past_time_executes_immediately(
        self, mock_send_task, client, operator_headers, db_session
    ):
        """Test that past execute_at time runs immediately."""
        mock_send_task.return_value = MagicMock()
        past_time = datetime.utcnow() - timedelta(hours=1)

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": ["show version"],
                "execute_at": past_time.isoformat(),
            },
            headers=operator_headers,
        )

        assert response.status_code == 202

        # Verify task was not scheduled (eta should be None)
        call_args = mock_send_task.call_args
        assert call_args[1].get("eta") is None

    def test_run_commands_empty_commands(self, client, operator_headers):
        """Test that empty commands list is rejected."""
        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {"hostnames": ["router1"]},
                "commands": [],
            },
            headers=operator_headers,
        )
        assert response.status_code == 422

    @patch("app.api.commands.celery_app.send_task")
    def test_run_commands_multiple_targets(
        self, mock_send_task, client, operator_headers, db_session
    ):
        """Test running commands with multiple target filters."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/commands/run",
            json={
                "targets": {
                    "hostnames": ["router1"],
                    "vendors": ["cisco"],
                    "platforms": ["ios"],
                },
                "commands": ["show version"],
            },
            headers=operator_headers,
        )

        assert response.status_code == 202

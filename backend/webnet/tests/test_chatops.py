"""Tests for ChatOps integration."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.chatops.models import SlackWorkspace, SlackChannel, SlackUserMapping
from webnet.devices.models import Device, Credential
from webnet.jobs.models import Job

User = get_user_model()


@pytest.fixture
def customer(db):
    """Create a test customer."""
    return Customer.objects.create(name="Test Customer")


@pytest.fixture
def user(db, customer):
    """Create a test user."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass",
        role="admin",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def slack_workspace(db, customer):
    """Create a test Slack workspace."""
    return SlackWorkspace.objects.create(
        customer=customer,
        team_id="T12345",
        team_name="Test Team",
        bot_token="xoxb-test-token",
        bot_user_id="U12345",
        signing_secret="test-secret",
        enabled=True,
    )


@pytest.fixture
def slack_channel(db, slack_workspace):
    """Create a test Slack channel."""
    return SlackChannel.objects.create(
        workspace=slack_workspace,
        channel_id="C12345",
        channel_name="general",
        notify_job_completion=True,
        notify_job_failure=True,
        notify_compliance_violations=True,
        notify_drift_detected=True,
    )


@pytest.fixture
def slack_user_mapping(db, slack_workspace, user):
    """Create a test Slack user mapping."""
    return SlackUserMapping.objects.create(
        workspace=slack_workspace,
        slack_user_id="U67890",
        user=user,
    )


@pytest.fixture
def device(db, customer):
    """Create a test device."""
    cred = Credential.objects.create(
        customer=customer,
        name="test-cred",
        username="admin",
        password="password",
    )
    return Device.objects.create(
        customer=customer,
        hostname="test-device",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        role="router",
        site="site1",
        credential=cred,
        enabled=True,
    )


@pytest.mark.django_db
class TestSlackWorkspaceAPI:
    """Test SlackWorkspace API endpoints."""

    def test_list_workspaces(self, user, slack_workspace):
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/chatops/workspaces/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["team_name"] == "Test Team"

    def test_create_workspace(self, user, customer):
        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "customer": customer.id,
            "team_id": "T99999",
            "team_name": "New Team",
            "bot_token": "xoxb-new-token",
            "bot_user_id": "U99999",
            "signing_secret": "new-secret",
            "enabled": True,
        }

        response = client.post("/api/v1/chatops/workspaces/", data)
        assert response.status_code == 201
        assert SlackWorkspace.objects.filter(team_id="T99999").exists()


@pytest.mark.django_db
class TestSlackCommands:
    """Test Slack command handlers."""

    def test_status_command(self, slack_workspace, slack_user_mapping, user, device):
        from webnet.chatops.commands import StatusCommandHandler

        # Mock the has_perm method to return True
        with patch.object(user, "has_perm", return_value=True):
            handler = StatusCommandHandler(
                workspace=slack_workspace,
                user=user,
                slack_user_id="U67890",
                channel_id="C12345",
            )

            result = handler.handle(["test-device"])
            assert "blocks" in result
            assert "test-device" in str(result)

    def test_jobs_command(self, slack_workspace, slack_user_mapping, user, customer):
        from webnet.chatops.commands import JobsCommandHandler

        # Create a test job
        Job.objects.create(
            customer=customer,
            type="run_commands",
            status="success",
            user=user,
        )

        handler = JobsCommandHandler(
            workspace=slack_workspace,
            user=user,
            slack_user_id="U67890",
            channel_id="C12345",
        )

        result = handler.handle([])
        assert "blocks" in result
        assert "text" in result

    def test_help_command(self, slack_workspace, user):
        from webnet.chatops.commands import HelpCommandHandler

        handler = HelpCommandHandler(
            workspace=slack_workspace,
            user=user,
            slack_user_id="U67890",
            channel_id="C12345",
        )

        result = handler.handle([])
        assert "blocks" in result
        assert "help" in result["text"].lower() or "commands" in result["text"].lower()

    @patch("webnet.chatops.commands.JobService")
    def test_backup_command(
        self, mock_job_service, slack_workspace, slack_user_mapping, user, device
    ):
        from webnet.chatops.commands import BackupCommandHandler

        # Mock job creation
        mock_job = MagicMock()
        mock_job.id = 123
        mock_job_service.return_value.create_job.return_value = mock_job

        handler = BackupCommandHandler(
            workspace=slack_workspace,
            user=user,
            slack_user_id="U67890",
            channel_id="C12345",
        )

        result = handler.handle(["test-device"])
        assert "blocks" in result
        assert "backup" in result["text"].lower()


@pytest.mark.django_db
class TestSlackService:
    """Test Slack service functions."""

    def test_verify_request(self):
        from webnet.chatops.slack_service import SlackService
        import time
        import hmac
        import hashlib

        signing_secret = "test-secret"
        timestamp = str(int(time.time()))
        body = "test=data"

        sig_basestring = f"v0:{timestamp}:{body}"
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        result = SlackService.verify_request(body, timestamp, signature, signing_secret)
        assert result is True

    def test_verify_request_old_timestamp(self):
        from webnet.chatops.slack_service import SlackService
        import time

        signing_secret = "test-secret"
        timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        body = "test=data"
        signature = "v0=fake"

        result = SlackService.verify_request(body, timestamp, signature, signing_secret)
        assert result is False

    def test_format_job_completion_message(self, customer, user):
        from webnet.chatops.slack_service import SlackService
        from django.utils import timezone

        job = Job.objects.create(
            customer=customer,
            type="config_backup",
            status="success",
            user=user,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        result = SlackService.format_job_completion_message(job)
        assert "blocks" in result
        assert "text" in result
        assert "success" in result["text"].lower()

    def test_format_device_status_message(self, device):
        from webnet.chatops.slack_service import SlackService

        result = SlackService.format_device_status_message(device)
        assert "blocks" in result
        assert "text" in result
        assert "test-device" in result["text"]


@pytest.mark.django_db
class TestSlackWebhooks:
    """Test Slack webhook endpoints."""

    @patch("webnet.chatops.views.SlackService.verify_request")
    @patch("webnet.chatops.views.dispatch_command")
    def test_slack_command_webhook(
        self, mock_dispatch, mock_verify, slack_workspace, slack_user_mapping
    ):
        from django.test import Client

        mock_verify.return_value = True
        mock_dispatch.return_value = {"blocks": [], "text": "Success"}

        client = Client()
        response = client.post(
            "/api/v1/chatops/slack/commands",
            {
                "team_id": "T12345",
                "user_id": "U67890",
                "channel_id": "C12345",
                "text": "help",
            },
            HTTP_X_SLACK_REQUEST_TIMESTAMP=str(int(__import__("time").time())),
            HTTP_X_SLACK_SIGNATURE="v0=fake",
        )

        assert response.status_code == 200
        data = response.json()
        assert "response_type" in data

    def test_slack_events_webhook_verification(self):
        from django.test import Client

        client = Client()
        response = client.post(
            "/api/v1/chatops/slack/events",
            json.dumps({"type": "url_verification", "challenge": "test-challenge"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test-challenge"


@pytest.mark.django_db
class TestNotifications:
    """Test notification system."""

    @patch("webnet.chatops.slack_service.SlackService.send_message")
    def test_job_completion_notification(self, mock_send, customer, user, slack_channel):
        from webnet.chatops.slack_service import notify_job_completion
        from django.utils import timezone

        job = Job.objects.create(
            customer=customer,
            type="config_backup",
            status="success",
            user=user,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        notify_job_completion(job)

        # Verify that send_message was called
        assert mock_send.called

    @patch("webnet.chatops.slack_service.SlackService.send_message")
    def test_job_failure_notification(self, mock_send, customer, user, slack_channel):
        from webnet.chatops.slack_service import notify_job_completion
        from django.utils import timezone

        job = Job.objects.create(
            customer=customer,
            type="config_backup",
            status="failed",
            user=user,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        notify_job_completion(job)

        # Verify that send_message was called for failure
        assert mock_send.called

    @patch("webnet.chatops.slack_service.SlackService.send_message")
    def test_compliance_violation_notification(
        self, mock_send, customer, user, device, slack_channel
    ):
        from webnet.chatops.slack_service import notify_compliance_violation
        from webnet.compliance.models import CompliancePolicy, ComplianceResult
        from webnet.jobs.models import Job

        # Create a compliance policy
        policy = CompliancePolicy.objects.create(
            customer=customer,
            name="Test Policy",
            scope_json={"role": "router"},
            definition_yaml="test: value",
            created_by=user,
        )

        # Create a job
        job = Job.objects.create(
            customer=customer,
            type="compliance_check",
            status="success",
            user=user,
        )

        # Create a compliance result with violation
        result = ComplianceResult.objects.create(
            policy=policy,
            device=device,
            job=job,
            status="fail",
            details_json={"violation": "test"},
        )

        notify_compliance_violation(result)

        # Verify that send_message was called
        assert mock_send.called

    @patch("webnet.chatops.slack_service.SlackService.send_message")
    def test_drift_detection_notification(self, mock_send, customer, user, device, slack_channel):
        from webnet.chatops.slack_service import notify_drift_detected
        from webnet.config_mgmt.models import ConfigSnapshot, ConfigDrift
        from webnet.jobs.models import Job

        # Create a job for the snapshots
        job = Job.objects.create(
            customer=customer,
            type="config_backup",
            status="success",
            user=user,
        )

        # Create snapshots
        snapshot1 = ConfigSnapshot.objects.create(
            device=device,
            job=job,
            config_text="config line 1\nconfig line 2",
            hash="hash1",
        )

        snapshot2 = ConfigSnapshot.objects.create(
            device=device,
            job=job,
            config_text="config line 1\nconfig line 2\nconfig line 3",
            hash="hash2",
        )

        # Create drift
        drift = ConfigDrift.objects.create(
            device=device,
            snapshot_from=snapshot1,
            snapshot_to=snapshot2,
            additions=1,
            deletions=0,
            changes=1,
            total_lines=3,
            has_changes=True,
            diff_summary="Added config line 3",
            triggered_by=user,
        )

        notify_drift_detected(drift)

        # Verify that send_message was called
        assert mock_send.called

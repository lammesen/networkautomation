"""Tests for the audit logging module."""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.audit import (
    AuditAction,
    AuditContext,
    AuditEvent,
    AuditLogger,
    AuditOutcome,
    audit_log,
    create_audit_context_from_request,
    get_audit_logger,
    mask_sensitive_data,
)


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_auth_actions(self) -> None:
        """Test authentication action values."""
        assert AuditAction.LOGIN_SUCCESS.value == "auth.login.success"
        assert AuditAction.LOGIN_FAILURE.value == "auth.login.failure"
        assert AuditAction.TOKEN_REFRESH.value == "auth.token.refresh"

    def test_user_actions(self) -> None:
        """Test user management action values."""
        assert AuditAction.USER_CREATE.value == "user.create"
        assert AuditAction.USER_UPDATE.value == "user.update"
        assert AuditAction.USER_ROLE_CHANGE.value == "user.role.change"

    def test_device_actions(self) -> None:
        """Test device action values."""
        assert AuditAction.DEVICE_CREATE.value == "device.create"
        assert AuditAction.DEVICE_DELETE.value == "device.delete"

    def test_config_actions(self) -> None:
        """Test config action values."""
        assert AuditAction.CONFIG_BACKUP.value == "config.backup"
        assert AuditAction.CONFIG_DEPLOY_COMMIT.value == "config.deploy.commit"
        assert AuditAction.CONFIG_ROLLBACK_COMMIT.value == "config.rollback.commit"


class TestAuditOutcome:
    """Tests for AuditOutcome enum."""

    def test_outcome_values(self) -> None:
        """Test outcome enum values."""
        assert AuditOutcome.SUCCESS.value == "success"
        assert AuditOutcome.FAILURE.value == "failure"
        assert AuditOutcome.DENIED.value == "denied"
        assert AuditOutcome.ERROR.value == "error"


class TestAuditContext:
    """Tests for AuditContext dataclass."""

    def test_context_with_all_fields(self) -> None:
        """Test creating context with all fields."""
        context = AuditContext(
            user_id=1,
            username="admin",
            user_role="admin",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            customer_id=10,
            customer_name="Acme Corp",
        )
        assert context.user_id == 1
        assert context.username == "admin"
        assert context.customer_name == "Acme Corp"

    def test_context_with_minimal_fields(self) -> None:
        """Test creating context with no fields."""
        context = AuditContext()
        assert context.user_id is None
        assert context.username is None


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_event_creation(self) -> None:
        """Test creating an audit event."""
        context = AuditContext(user_id=1, username="admin")
        event = AuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            outcome=AuditOutcome.SUCCESS,
            context=context,
        )
        assert event.action == AuditAction.LOGIN_SUCCESS
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.context.username == "admin"
        assert event.timestamp is not None

    def test_event_to_dict(self) -> None:
        """Test converting event to dictionary."""
        context = AuditContext(user_id=1, username="admin", user_role="admin")
        event = AuditEvent(
            action=AuditAction.DEVICE_CREATE,
            outcome=AuditOutcome.SUCCESS,
            context=context,
            resource_type="device",
            resource_id="123",
            resource_name="router1",
            details={"vendor": "cisco"},
        )
        data = event.to_dict()

        assert data["audit"] is True
        assert data["action"] == "device.create"
        assert data["outcome"] == "success"
        assert data["context"]["user_id"] == 1
        assert data["context"]["username"] == "admin"
        assert data["resource"]["type"] == "device"
        assert data["resource"]["id"] == "123"
        assert data["details"]["vendor"] == "cisco"

    def test_event_to_dict_with_old_new_values(self) -> None:
        """Test event dict includes old/new values for updates."""
        context = AuditContext(user_id=1, username="admin")
        event = AuditEvent(
            action=AuditAction.USER_UPDATE,
            outcome=AuditOutcome.SUCCESS,
            context=context,
            resource_type="user",
            resource_id="5",
            old_value={"role": "viewer"},
            new_value={"role": "operator"},
        )
        data = event.to_dict()

        assert data["old_value"] == {"role": "viewer"}
        assert data["new_value"] == {"role": "operator"}

    def test_event_to_dict_with_error(self) -> None:
        """Test event dict includes error message."""
        context = AuditContext(user_id=1, username="admin")
        event = AuditEvent(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.ERROR,
            context=context,
            error_message="Database connection failed",
        )
        data = event.to_dict()

        assert data["error"] == "Database connection failed"


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_log_success_event(self) -> None:
        """Test logging a success event."""
        logger = AuditLogger()
        context = AuditContext(user_id=1, username="admin")
        event = AuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            outcome=AuditOutcome.SUCCESS,
            context=context,
        )

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(event)
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "auth.login.success" in call_args[0][0]

    def test_log_failure_event(self) -> None:
        """Test logging a failure event uses warning level."""
        logger = AuditLogger()
        context = AuditContext(username="attacker")
        event = AuditEvent(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            context=context,
        )

        with patch.object(logger._logger, "warning") as mock_warning:
            logger.log(event)
            mock_warning.assert_called_once()

    def test_log_error_event(self) -> None:
        """Test logging an error event uses error level."""
        logger = AuditLogger()
        context = AuditContext(user_id=1, username="admin")
        event = AuditEvent(
            action=AuditAction.DEVICE_CREATE,
            outcome=AuditOutcome.ERROR,
            context=context,
            error_message="Database error",
        )

        with patch.object(logger._logger, "error") as mock_error:
            logger.log(event)
            mock_error.assert_called_once()

    def test_log_action_convenience_method(self) -> None:
        """Test log_action convenience method."""
        logger = AuditLogger()
        context = AuditContext(user_id=1, username="admin")

        with patch.object(logger, "log") as mock_log:
            logger.log_action(
                action=AuditAction.DEVICE_DELETE,
                outcome=AuditOutcome.SUCCESS,
                context=context,
                resource_type="device",
                resource_id="123",
            )
            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.action == AuditAction.DEVICE_DELETE
            assert event.resource_id == "123"


class TestAuditLogFunction:
    """Tests for the global audit_log function."""

    def test_audit_log_creates_event(self) -> None:
        """Test audit_log convenience function."""
        with patch("app.core.audit.get_audit_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            audit_log(
                AuditAction.CREDENTIAL_CREATE,
                AuditOutcome.SUCCESS,
                user_id=1,
                username="admin",
                resource_type="credential",
                resource_id="5",
            )

            mock_logger.log_action.assert_called_once()
            call_kwargs = mock_logger.log_action.call_args[1]
            assert call_kwargs["action"] == AuditAction.CREDENTIAL_CREATE
            assert call_kwargs["resource_type"] == "credential"


class TestCreateAuditContextFromRequest:
    """Tests for create_audit_context_from_request helper."""

    def test_with_x_forwarded_for(self) -> None:
        """Test IP extraction from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"x-forwarded-for": "203.0.113.1, 10.0.0.1", "user-agent": "TestAgent"}
        request.client = MagicMock(host="127.0.0.1")

        context = create_audit_context_from_request(request)

        assert context.ip_address == "203.0.113.1"
        assert context.user_agent == "TestAgent"

    def test_with_client_host(self) -> None:
        """Test IP extraction from client host when no X-Forwarded-For."""
        request = MagicMock()
        request.headers = {"user-agent": "TestAgent"}
        request.client = MagicMock(host="192.168.1.100")

        context = create_audit_context_from_request(request)

        assert context.ip_address == "192.168.1.100"

    def test_with_user_and_customer(self) -> None:
        """Test context creation with user and customer objects."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="10.0.0.1")

        user = MagicMock()
        user.id = 42
        user.username = "operator1"
        user.role = "operator"

        customer = MagicMock()
        customer.id = 10
        customer.name = "Acme Corp"

        context = create_audit_context_from_request(request, user=user, customer=customer)

        assert context.user_id == 42
        assert context.username == "operator1"
        assert context.user_role == "operator"
        assert context.customer_id == 10
        assert context.customer_name == "Acme Corp"

    def test_with_request_id(self) -> None:
        """Test request ID extraction from headers."""
        request = MagicMock()
        request.headers = {"x-request-id": "req-abc-123"}
        request.client = None

        context = create_audit_context_from_request(request)

        assert context.request_id == "req-abc-123"


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data helper."""

    def test_masks_password(self) -> None:
        """Test that password fields are masked."""
        data = {"username": "admin", "password": "secret123"}
        masked = mask_sensitive_data(data)

        assert masked["username"] == "admin"
        assert masked["password"] == "***MASKED***"

    def test_masks_nested_sensitive_fields(self) -> None:
        """Test masking works on nested dictionaries."""
        data = {"user": {"name": "admin", "api_key": "key123"}}
        masked = mask_sensitive_data(data)

        assert masked["user"]["name"] == "admin"
        assert masked["user"]["api_key"] == "***MASKED***"

    def test_masks_partial_match(self) -> None:
        """Test masking works on partial key matches."""
        data = {"enable_password": "cisco", "ssh_private_key": "-----BEGIN"}
        masked = mask_sensitive_data(data)

        assert masked["enable_password"] == "***MASKED***"
        assert masked["ssh_private_key"] == "***MASKED***"

    def test_custom_sensitive_keys(self) -> None:
        """Test custom sensitive key set."""
        data = {"custom_secret": "value", "normal": "data"}
        masked = mask_sensitive_data(data, sensitive_keys={"custom_secret"})

        assert masked["custom_secret"] == "***MASKED***"
        assert masked["normal"] == "data"

    def test_non_sensitive_preserved(self) -> None:
        """Test non-sensitive data is preserved."""
        data = {"hostname": "router1", "vendor": "cisco", "site": "dc1"}
        masked = mask_sensitive_data(data)

        assert masked == data


class TestGetAuditLogger:
    """Tests for get_audit_logger singleton."""

    def test_returns_same_instance(self) -> None:
        """Test that get_audit_logger returns the same instance."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_logger_is_audit_logger_type(self) -> None:
        """Test that returned logger is an AuditLogger."""
        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)

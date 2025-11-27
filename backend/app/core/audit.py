"""Audit logging for sensitive operations.

This module provides structured audit logging for security-sensitive operations.
Audit logs are designed to be immutable, queryable, and suitable for compliance.

Audit events capture:
- Who performed the action (user_id, username, role)
- What action was performed (action type, resource type)
- When it happened (timestamp)
- Where it originated (IP address, user agent)
- What changed (before/after state, resource identifiers)
- Outcome (success/failure, error details)
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .logging import get_logger


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    PASSWORD_CHANGE = "auth.password.change"

    # User Management
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ACTIVATE = "user.activate"
    USER_DEACTIVATE = "user.deactivate"
    USER_ROLE_CHANGE = "user.role.change"

    # Customer Management
    CUSTOMER_CREATE = "customer.create"
    CUSTOMER_UPDATE = "customer.update"
    CUSTOMER_DELETE = "customer.delete"
    CUSTOMER_USER_ADD = "customer.user.add"
    CUSTOMER_USER_REMOVE = "customer.user.remove"
    CUSTOMER_IP_RANGE_ADD = "customer.ip_range.add"
    CUSTOMER_IP_RANGE_DELETE = "customer.ip_range.delete"

    # Device Management
    DEVICE_CREATE = "device.create"
    DEVICE_UPDATE = "device.update"
    DEVICE_DELETE = "device.delete"
    DEVICE_IMPORT = "device.import"

    # Credential Management
    CREDENTIAL_CREATE = "credential.create"
    CREDENTIAL_UPDATE = "credential.update"
    CREDENTIAL_DELETE = "credential.delete"

    # Command Execution
    COMMAND_EXECUTE = "command.execute"
    COMMAND_SCHEDULE = "command.schedule"

    # Configuration Management
    CONFIG_BACKUP = "config.backup"
    CONFIG_DEPLOY_PREVIEW = "config.deploy.preview"
    CONFIG_DEPLOY_COMMIT = "config.deploy.commit"
    CONFIG_ROLLBACK_PREVIEW = "config.rollback.preview"
    CONFIG_ROLLBACK_COMMIT = "config.rollback.commit"

    # Compliance
    COMPLIANCE_CHECK = "compliance.check"
    COMPLIANCE_POLICY_CREATE = "compliance.policy.create"
    COMPLIANCE_POLICY_UPDATE = "compliance.policy.update"
    COMPLIANCE_POLICY_DELETE = "compliance.policy.delete"

    # Access Control
    ACCESS_DENIED = "access.denied"
    UNAUTHORIZED_ACCESS = "access.unauthorized"


class AuditOutcome(str, Enum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"


@dataclass
class AuditContext:
    """Context information for audit events.

    Captures who performed the action and from where.
    """

    user_id: Optional[int] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None


@dataclass
class AuditEvent:
    """Represents a single audit log entry.

    Immutable record of a security-relevant action.
    """

    action: AuditAction
    outcome: AuditOutcome
    context: AuditContext
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging/storage."""
        data = {
            "audit": True,  # Marker for log filtering
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "outcome": self.outcome.value,
            "context": asdict(self.context),
        }

        if self.resource_type:
            data["resource"] = {
                "type": self.resource_type,
                "id": self.resource_id,
                "name": self.resource_name,
            }

        if self.details:
            data["details"] = self.details

        if self.old_value is not None:
            data["old_value"] = self.old_value

        if self.new_value is not None:
            data["new_value"] = self.new_value

        if self.error_message:
            data["error"] = self.error_message

        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms

        return data


class AuditLogger:
    """Logger for audit events.

    Provides a structured interface for logging security-sensitive operations.
    Audit logs are written to a dedicated logger and can be routed to
    separate storage (file, database, SIEM) for compliance.
    """

    def __init__(self, logger_name: str = "audit") -> None:
        """Initialize audit logger.

        Args:
            logger_name: Name for the audit logger. Defaults to 'audit'.
        """
        self._logger = get_logger(f"app.{logger_name}")
        # Ensure audit logs are always at least INFO level
        self._logger.setLevel(logging.INFO)

    def log(self, event: AuditEvent) -> None:
        """Log an audit event.

        Args:
            event: The audit event to log.
        """
        log_data = event.to_dict()

        # Determine log level based on outcome
        if event.outcome == AuditOutcome.ERROR:
            self._logger.error(
                f"AUDIT: {event.action.value} - {event.outcome.value}",
                extra=log_data,
            )
        elif event.outcome in (AuditOutcome.FAILURE, AuditOutcome.DENIED):
            self._logger.warning(
                f"AUDIT: {event.action.value} - {event.outcome.value}",
                extra=log_data,
            )
        else:
            self._logger.info(
                f"AUDIT: {event.action.value} - {event.outcome.value}",
                extra=log_data,
            )

    def log_action(
        self,
        action: AuditAction,
        outcome: AuditOutcome,
        context: AuditContext,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        old_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Convenience method to log an action with all parameters.

        Args:
            action: Type of action being performed.
            outcome: Result of the action.
            context: Who/where context.
            resource_type: Type of resource affected (e.g., 'device', 'user').
            resource_id: Identifier of the affected resource.
            resource_name: Human-readable name of the resource.
            details: Additional details about the action.
            old_value: Previous state (for updates).
            new_value: New state (for creates/updates).
            error_message: Error details if action failed.
            duration_ms: How long the action took.
        """
        event = AuditEvent(
            action=action,
            outcome=outcome,
            context=context,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details or {},
            old_value=old_value,
            new_value=new_value,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log(event)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance.

    Returns:
        The singleton AuditLogger instance.
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(
    action: AuditAction,
    outcome: AuditOutcome,
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    customer_id: Optional[int] = None,
    customer_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    old_value: Optional[dict[str, Any]] = None,
    new_value: Optional[dict[str, Any]] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """Log an audit event using the global logger.

    Convenience function for quick audit logging without managing instances.

    Args:
        action: Type of action being performed.
        outcome: Result of the action.
        user_id: ID of the user performing the action.
        username: Username of the user performing the action.
        user_role: Role of the user (admin, operator, viewer).
        ip_address: IP address of the request.
        user_agent: User agent string from the request.
        request_id: Unique request identifier for correlation.
        customer_id: ID of the customer context.
        customer_name: Name of the customer.
        resource_type: Type of resource affected.
        resource_id: Identifier of the affected resource.
        resource_name: Human-readable name of the resource.
        details: Additional details about the action.
        old_value: Previous state (for updates).
        new_value: New state (for creates/updates).
        error_message: Error details if action failed.
        duration_ms: How long the action took.

    Example:
        >>> audit_log(
        ...     AuditAction.LOGIN_SUCCESS,
        ...     AuditOutcome.SUCCESS,
        ...     username="admin",
        ...     ip_address="192.168.1.1",
        ... )
    """
    context = AuditContext(
        user_id=user_id,
        username=username,
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        customer_id=customer_id,
        customer_name=customer_name,
    )
    get_audit_logger().log_action(
        action=action,
        outcome=outcome,
        context=context,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details,
        old_value=old_value,
        new_value=new_value,
        error_message=error_message,
        duration_ms=duration_ms,
    )


def create_audit_context_from_request(
    request: Any,
    user: Optional[Any] = None,
    customer: Optional[Any] = None,
) -> AuditContext:
    """Create an AuditContext from a FastAPI request and user.

    Args:
        request: FastAPI Request object.
        user: Optional User model instance.
        customer: Optional Customer model instance.

    Returns:
        Populated AuditContext.
    """
    # Extract IP from X-Forwarded-For header or client host
    ip_address = None
    if hasattr(request, "headers"):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        elif hasattr(request, "client") and request.client:
            ip_address = request.client.host

    user_agent = None
    if hasattr(request, "headers"):
        user_agent = request.headers.get("user-agent")

    request_id = None
    if hasattr(request, "headers"):
        request_id = request.headers.get("x-request-id")

    return AuditContext(
        user_id=user.id if user else None,
        username=user.username if user else None,
        user_role=user.role if user else None,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        customer_id=customer.id if customer else None,
        customer_name=customer.name if customer else None,
    )


def mask_sensitive_data(
    data: dict[str, Any], sensitive_keys: set[str] | None = None
) -> dict[str, Any]:
    """Mask sensitive fields in data before logging.

    Args:
        data: Dictionary containing data to mask.
        sensitive_keys: Set of keys to mask. Defaults to common sensitive fields.

    Returns:
        Copy of data with sensitive values masked.
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "password",
            "hashed_password",
            "secret",
            "token",
            "api_key",
            "private_key",
            "ssh_key",
            "enable_password",
        }

    masked = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys or any(s in key.lower() for s in sensitive_keys):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked[key] = value

    return masked

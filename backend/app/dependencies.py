"""Shared FastAPI dependency factories."""

from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.auth import (
    get_current_active_customer,
    get_current_user,
    get_optional_active_customer,
    require_admin,
    require_operator,
)
from app.db import Customer, User, get_db
from app.domain import MultiTenantContext, TenantRequestContext
from app.services import (
    ComplianceService,
    ConfigService,
    CredentialService,
    CustomerService,
    DeviceService,
    JobService,
    SSHSessionManager,
    UserService,
    get_ssh_session_manager,
)
from app.services.api_key_service import APIKeyService


def get_session(db: Session = Depends(get_db)) -> Session:
    """Expose the SQLAlchemy session (alias for clarity)."""
    return db


def get_tenant_context(
    current_user: User = Depends(get_current_user),
    active_customer: Customer = Depends(get_current_active_customer),
) -> TenantRequestContext:
    return TenantRequestContext(user=current_user, customer=active_customer)


def get_multi_tenant_context(
    current_user: User = Depends(get_current_user),
    active_customer: Optional[Customer] = Depends(get_optional_active_customer),
) -> MultiTenantContext:
    """Get a context that supports optional customer filtering.

    When no X-Customer-ID header is provided, returns a context that allows
    access to all customers the user has access to.
    """
    return MultiTenantContext(user=current_user, customer=active_customer)


def get_operator_context(
    current_user: User = Depends(require_operator),
    active_customer: Customer = Depends(get_current_active_customer),
) -> TenantRequestContext:
    return TenantRequestContext(user=current_user, customer=active_customer)


def get_admin_user(user: User = Depends(require_admin)) -> User:
    return user


def get_device_service(session: Session = Depends(get_session)) -> DeviceService:
    return DeviceService(session)


def get_credential_service(session: Session = Depends(get_session)) -> CredentialService:
    return CredentialService(session)


def get_customer_service(session: Session = Depends(get_session)) -> CustomerService:
    return CustomerService(session)


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_job_service(session: Session = Depends(get_session)) -> JobService:
    return JobService(session)


def get_ssh_manager() -> SSHSessionManager:
    """Provide the shared SSH session manager."""
    return get_ssh_session_manager()


def get_config_service(session: Session = Depends(get_session)) -> ConfigService:
    return ConfigService(session)


def get_compliance_service(session: Session = Depends(get_session)) -> ComplianceService:
    return ComplianceService(session)


def get_api_key_service(session: Session = Depends(get_session)) -> APIKeyService:
    return APIKeyService(session)

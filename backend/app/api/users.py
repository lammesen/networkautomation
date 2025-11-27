"""User management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from app.core.audit import AuditAction, AuditOutcome, audit_log
from app.db import User
from app.dependencies import get_admin_user, get_user_service
from app.schemas.auth import AdminUserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    active: Optional[bool] = None,
    service: UserService = Depends(get_user_service),
    _: User = Depends(get_admin_user),
) -> list[UserResponse]:
    """List users with optional active status filter."""
    users = service.list_users(active)
    return [UserResponse.model_validate(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    payload: AdminUserCreate,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(get_admin_user),
) -> UserResponse:
    """Create a new user (admin only)."""
    # Get IP for audit logging
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )

    user = service.admin_create_user(payload)

    audit_log(
        AuditAction.USER_CREATE,
        AuditOutcome.SUCCESS,
        user_id=admin.id,
        username=admin.username,
        user_role=admin.role,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        details={"registration_type": "admin_create"},
        new_value={"username": user.username, "role": user.role, "is_active": user.is_active},
    )

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: Request,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_admin: User = Depends(get_admin_user),
) -> UserResponse:
    """Update user details (role, status)."""
    # Get IP for audit logging
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )

    # Get old values before update
    old_user = service.get_user_by_id(user_id)
    old_values = {
        "role": old_user.role,
        "is_active": old_user.is_active,
    }

    user = service.update_user(user_id, payload, current_admin)

    # Determine specific action type
    action = AuditAction.USER_UPDATE
    if payload.role is not None and payload.role != old_values["role"]:
        action = AuditAction.USER_ROLE_CHANGE
    elif payload.is_active is not None and payload.is_active != old_values["is_active"]:
        action = AuditAction.USER_ACTIVATE if payload.is_active else AuditAction.USER_DEACTIVATE

    new_values = {
        "role": user.role,
        "is_active": user.is_active,
    }

    audit_log(
        action,
        AuditOutcome.SUCCESS,
        user_id=current_admin.id,
        username=current_admin.username,
        user_role=current_admin.role,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.username,
        old_value=old_values,
        new_value=new_values,
    )

    return UserResponse.model_validate(user)

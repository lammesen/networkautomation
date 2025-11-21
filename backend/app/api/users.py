"""User management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends

from app.api import errors
from app.db import User
from app.dependencies import get_admin_user, get_user_service
from app.domain.exceptions import DomainError
from app.schemas.auth import UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _handle_error(exc: DomainError):
    raise errors.to_http(exc)


@router.get("", response_model=list[UserResponse])
def list_users(
    active: Optional[bool] = None,
    service: UserService = Depends(get_user_service),
    _: User = Depends(get_admin_user),
) -> list[UserResponse]:
    """List users with optional active status filter."""
    users = service.list_users(active)
    return [UserResponse.model_validate(user) for user in users]


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_admin: User = Depends(get_admin_user),
) -> UserResponse:
    """Update user details (role, status)."""
    try:
        user = service.update_user(user_id, payload, current_admin)
        return UserResponse.model_validate(user)
    except DomainError as exc:
        _handle_error(exc)

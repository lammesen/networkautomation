"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_password,
)
from app.db import User, get_db
from app.dependencies import get_user_service
from app.domain.exceptions import ForbiddenError, UnauthorizedError
from app.repositories import UserRepository
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Login user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(user_login.username)

    if not user or not verify_password(user_login.password, user.hashed_password):
        raise UnauthorizedError("Incorrect username or password")

    if not user.is_active:
        raise ForbiddenError("Inactive user")

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user."""
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_create: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Register new user.

    New users are created as inactive and require admin approval.
    """
    new_user = service.create_user(user_create)
    return UserResponse.model_validate(new_user)

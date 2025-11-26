"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core import settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_password,
    verify_refresh_token,
)
from app.db import User, get_db
from app.dependencies import get_user_service
from app.domain.exceptions import ForbiddenError, UnauthorizedError
from app.repositories import UserRepository
from app.schemas.auth import RefreshTokenRequest, Token, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter for auth endpoints - disabled during testing
limiter = Limiter(key_func=get_remote_address, enabled=not settings.testing)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user_login: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Login user.

    Rate limited to 5 attempts per minute per IP to prevent brute force attacks.
    """
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


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh_token(
    request: Request, payload: RefreshTokenRequest, db: Session = Depends(get_db)
) -> Token:
    """Refresh access token using refresh token.

    Rate limited to 30 requests per minute per IP.
    """
    username = verify_refresh_token(payload.refresh_token)

    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)

    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise ForbiddenError("Inactive user")

    access_token = create_access_token(data={"sub": user.username})
    new_refresh_token = create_refresh_token(data={"sub": user.username})

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def register(
    request: Request,
    user_create: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Register new user.

    New users are created as inactive and require admin approval.
    Rate limited to 10 registrations per hour per IP.
    """
    new_user = service.create_user(user_create)
    return UserResponse.model_validate(new_user)

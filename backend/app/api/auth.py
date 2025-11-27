"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core import settings
from app.core.audit import (
    AuditAction,
    AuditOutcome,
    audit_log,
    create_audit_context_from_request,
)
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

    # Get IP for audit logging
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )

    if not user or not verify_password(user_login.password, user.hashed_password):
        # Log failed login attempt
        audit_log(
            AuditAction.LOGIN_FAILURE,
            AuditOutcome.FAILURE,
            username=user_login.username,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "invalid_credentials"},
        )
        raise UnauthorizedError("Incorrect username or password")

    if not user.is_active:
        # Log attempt to login to inactive account
        audit_log(
            AuditAction.LOGIN_FAILURE,
            AuditOutcome.DENIED,
            user_id=user.id,
            username=user.username,
            user_role=user.role,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "inactive_user"},
        )
        raise ForbiddenError("Inactive user")

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Log successful login
    audit_log(
        AuditAction.LOGIN_SUCCESS,
        AuditOutcome.SUCCESS,
        user_id=user.id,
        username=user.username,
        user_role=user.role,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

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
    # Get IP for audit logging
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )

    try:
        username = verify_refresh_token(payload.refresh_token)
    except Exception:
        audit_log(
            AuditAction.TOKEN_REFRESH,
            AuditOutcome.FAILURE,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "invalid_refresh_token"},
        )
        raise

    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)

    if not user:
        audit_log(
            AuditAction.TOKEN_REFRESH,
            AuditOutcome.FAILURE,
            username=username,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "user_not_found"},
        )
        raise UnauthorizedError("User not found")

    if not user.is_active:
        audit_log(
            AuditAction.TOKEN_REFRESH,
            AuditOutcome.DENIED,
            user_id=user.id,
            username=user.username,
            user_role=user.role,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "inactive_user"},
        )
        raise ForbiddenError("Inactive user")

    access_token = create_access_token(data={"sub": user.username})
    new_refresh_token = create_refresh_token(data={"sub": user.username})

    audit_log(
        AuditAction.TOKEN_REFRESH,
        AuditOutcome.SUCCESS,
        user_id=user.id,
        username=user.username,
        user_role=user.role,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )

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
    # Get IP for audit logging
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )

    try:
        new_user = service.create_user(user_create)

        audit_log(
            AuditAction.USER_CREATE,
            AuditOutcome.SUCCESS,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            resource_type="user",
            resource_id=str(new_user.id),
            resource_name=new_user.username,
            details={"registration_type": "self_register"},
        )

        return UserResponse.model_validate(new_user)
    except Exception as e:
        audit_log(
            AuditAction.USER_CREATE,
            AuditOutcome.FAILURE,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            resource_type="user",
            resource_name=user_create.username,
            details={"registration_type": "self_register"},
            error_message=str(e),
        )
        raise

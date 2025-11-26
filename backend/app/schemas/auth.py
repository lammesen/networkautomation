"""Authentication schemas."""

import re

from pydantic import BaseModel, Field, field_validator

from app.schemas.customer import CustomerResponse


# Username pattern: alphanumeric with underscores and hyphens
USERNAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]*$")


def validate_password_complexity(password: str) -> str:
    """Validate password meets complexity requirements.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class Token(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data."""

    username: str | None = None


class UserLogin(BaseModel):
    """User login request."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """User response."""

    id: int
    username: str
    role: str
    is_active: bool
    customers: list[CustomerResponse] = []

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """User creation request."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(default="viewer", pattern="^(viewer|operator|admin)$")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, underscores, or hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class AdminUserCreate(BaseModel):
    """Admin user creation request - allows setting role and active status."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(default="viewer", pattern="^(viewer|operator|admin)$")
    is_active: bool = Field(default=True)
    customer_ids: list[int] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, underscores, or hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserUpdate(BaseModel):
    """User update request."""

    role: str | None = Field(None, pattern="^(viewer|operator|admin)$")
    is_active: bool | None = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., min_length=1)

"""Authentication schemas."""

from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """User creation request."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(default="viewer", pattern="^(viewer|operator|admin)$")

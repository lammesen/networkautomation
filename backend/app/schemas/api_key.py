"""Schemas for API key operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100, description="Descriptive name for the key")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration datetime")
    scopes: Optional[dict] = Field(None, description="Optional scope restrictions")


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)."""

    id: int
    name: str
    key_prefix: str
    scopes: Optional[dict]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(BaseModel):
    """Schema for newly created API key (includes the actual key).

    WARNING: The key field is only returned once at creation time.
    Store it securely - it cannot be retrieved again.
    """

    id: int
    name: str
    key: str = Field(..., description="The API key. Store securely - shown only once!")
    key_prefix: str
    scopes: Optional[dict]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

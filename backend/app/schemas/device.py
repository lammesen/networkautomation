"""Device schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CredentialBase(BaseModel):
    """Base credential schema."""

    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)


class CredentialCreate(CredentialBase):
    """Credential creation schema."""

    password: str = Field(..., min_length=1)
    enable_password: Optional[str] = None


class CredentialUpdate(BaseModel):
    """Credential update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1)
    enable_password: Optional[str] = None


class CredentialResponse(CredentialBase):
    """Credential response schema."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    """Base device schema."""

    hostname: str = Field(..., min_length=1, max_length=255)
    mgmt_ip: str = Field(..., min_length=7, max_length=45)
    vendor: str = Field(..., min_length=1, max_length=50)
    platform: str = Field(..., min_length=1, max_length=50)
    role: Optional[str] = Field(None, max_length=50)
    site: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = None
    enabled: bool = True


class DeviceCreate(DeviceBase):
    """Device creation schema."""

    credentials_ref: int = Field(..., gt=0)


class DeviceUpdate(BaseModel):
    """Device update schema."""

    hostname: Optional[str] = Field(None, min_length=1, max_length=255)
    mgmt_ip: Optional[str] = Field(None, min_length=7, max_length=45)
    vendor: Optional[str] = Field(None, min_length=1, max_length=50)
    platform: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[str] = Field(None, max_length=50)
    site: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = None
    credentials_ref: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None


class DeviceResponse(DeviceBase):
    """Device response schema."""

    id: int
    credentials_ref: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    """Device list response."""

    total: int
    devices: list[DeviceResponse]

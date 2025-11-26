"""Device schemas."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Validation patterns
HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)
IP_PATTERN = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
# Alphanumeric with underscores, hyphens, and dots for credential/vendor/platform names
SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$")


def validate_hostname_or_ip(value: str) -> str:
    """Validate that value is a valid hostname or IP address."""
    if IP_PATTERN.match(value):
        return value
    if HOSTNAME_PATTERN.match(value):
        return value
    raise ValueError("Must be a valid hostname or IPv4 address")


def validate_safe_name(value: str) -> str:
    """Validate name contains only safe characters."""
    if not SAFE_NAME_PATTERN.match(value):
        raise ValueError(
            "Must start with alphanumeric and contain only letters, numbers, underscores, hyphens, or dots"
        )
    return value


class CredentialBase(BaseModel):
    """Base credential schema."""

    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_safe_name(v)


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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_safe_name(v)
        return v


class CredentialResponse(CredentialBase):
    """Credential response schema."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    """Base device schema."""

    hostname: str = Field(..., min_length=1, max_length=255)
    mgmt_ip: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Management address (hostname or IP)",
    )
    vendor: str = Field(..., min_length=1, max_length=50)
    platform: str = Field(..., min_length=1, max_length=50)
    role: Optional[str] = Field(None, max_length=50)
    site: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = None
    enabled: bool = True

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        if not HOSTNAME_PATTERN.match(v):
            raise ValueError("Invalid hostname format")
        return v

    @field_validator("mgmt_ip")
    @classmethod
    def validate_mgmt_ip(cls, v: str) -> str:
        return validate_hostname_or_ip(v)

    @field_validator("vendor", "platform")
    @classmethod
    def validate_vendor_platform(cls, v: str) -> str:
        return validate_safe_name(v)


class DeviceCreate(DeviceBase):
    """Device creation schema."""

    credentials_ref: int = Field(..., gt=0)


class DeviceUpdate(BaseModel):
    """Device update schema."""

    hostname: Optional[str] = Field(None, min_length=1, max_length=255)
    mgmt_ip: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Management address (hostname or IP)",
    )
    vendor: Optional[str] = Field(None, min_length=1, max_length=50)
    platform: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[str] = Field(None, max_length=50)
    site: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = None
    credentials_ref: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HOSTNAME_PATTERN.match(v):
            raise ValueError("Invalid hostname format")
        return v

    @field_validator("mgmt_ip")
    @classmethod
    def validate_mgmt_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_hostname_or_ip(v)
        return v

    @field_validator("vendor", "platform")
    @classmethod
    def validate_vendor_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_safe_name(v)
        return v


class DeviceResponse(DeviceBase):
    """Device response schema."""

    id: int
    credentials_ref: int
    reachability_status: Optional[str] = None
    last_reachability_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    """Device list response."""

    total: int
    devices: list[DeviceResponse]

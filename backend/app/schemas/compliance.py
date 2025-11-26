"""Compliance schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Schema for creating a compliance policy."""

    name: str = Field(..., min_length=1, max_length=255)
    definition_yaml: str = Field(..., min_length=1, description="NAPALM validation YAML")
    scope_json: dict = Field(..., description="Device filters for policy scope")
    description: Optional[str] = Field(default=None, max_length=1000)


class PolicyUpdate(BaseModel):
    """Schema for updating a compliance policy."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    definition_yaml: Optional[str] = Field(None, min_length=1)
    scope_json: Optional[dict] = None
    description: Optional[str] = Field(default=None, max_length=1000)


class PolicyResponse(BaseModel):
    """Schema for compliance policy response."""

    id: int
    name: str
    description: Optional[str] = None
    scope_json: dict
    definition_yaml: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    """Schema for compliance policy list response (without definition_yaml)."""

    id: int
    name: str
    description: Optional[str] = None
    scope_json: dict
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceResultResponse(BaseModel):
    """Schema for compliance result response."""

    id: int
    policy_id: int
    device_id: int
    job_id: int
    ts: datetime
    status: str
    details_json: dict

    model_config = {"from_attributes": True}


class RunComplianceRequest(BaseModel):
    """Schema for running a compliance check."""

    policy_id: int = Field(..., description="Policy ID to run")


class DeviceComplianceSummary(BaseModel):
    """Schema for device compliance summary."""

    device_id: int
    policies: list[dict]

"""Job schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class JobBase(BaseModel):
    """Base job schema."""

    type: str
    target_summary_json: Optional[dict] = None
    payload_json: Optional[dict] = None


class JobCreate(JobBase):
    """Job creation schema."""

    user_id: int


class JobResponse(JobBase):
    """Job response schema."""

    id: int
    status: str
    user_id: int
    requested_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_summary_json: Optional[dict] = None

    model_config = {"from_attributes": True}


class JobLogResponse(BaseModel):
    """Job log response schema."""

    id: int
    job_id: int
    ts: datetime
    level: str
    host: Optional[str] = None
    message: str
    extra_json: Optional[dict] = None

    model_config = {"from_attributes": True}


class CommandRunRequest(BaseModel):
    """Request to run commands."""

    targets: dict = Field(..., description="Device filters (site, role, vendor, device_ids)")
    commands: list[str] = Field(..., min_length=1, description="Commands to execute")
    timeout_sec: Optional[int] = Field(default=30, description="Command timeout in seconds")


class ConfigBackupRequest(BaseModel):
    """Request to backup configurations."""

    targets: dict = Field(default_factory=dict, description="Device filters")
    source_label: str = Field(default="manual", description="Source label for backup")


class ConfigDeployPreviewRequest(BaseModel):
    """Request to preview config deployment."""

    targets: dict = Field(..., description="Device filters")
    mode: str = Field(default="merge", pattern="^(merge|replace)$")
    snippet: str = Field(..., description="Configuration snippet to deploy")


class ConfigDeployCommitRequest(BaseModel):
    """Request to commit config deployment."""

    previous_job_id: int = Field(..., description="Previous preview job ID")
    confirm: bool = Field(..., description="Confirmation flag")

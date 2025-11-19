from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.db.models import JobType, JobStatus


class JobBase(BaseModel):
    type: JobType
    target_summary_json: Optional[Dict[str, Any]] = None


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: int
    status: JobStatus
    user_id: int
    requested_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_summary_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class JobLog(BaseModel):
    id: int
    ts: datetime
    level: str
    message: str
    host: Optional[str] = None
    extra_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

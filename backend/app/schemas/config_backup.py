from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class ConfigBackupRequest(BaseModel):
    targets: Dict
    source_label: Optional[str] = "manual"

class ConfigSnapshot(BaseModel):
    id: int
    device_id: int
    created_at: datetime
    job_id: Optional[int]
    source: Optional[str]
    hash: str

    class Config:
        from_attributes = True

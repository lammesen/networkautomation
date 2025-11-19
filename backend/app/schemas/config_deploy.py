from pydantic import BaseModel
from typing import Dict, Optional

class ConfigDeployPreviewRequest(BaseModel):
    targets: Dict
    mode: str = "merge"
    snippet: str

class ConfigDeployCommitRequest(BaseModel):
    previous_job_id: int
    confirm: bool = True

from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

from app.db.models import ComplianceStatus

class CompliancePolicyBase(BaseModel):
    name: str
    scope_json: Dict[str, Any]
    definition_yaml: str

class CompliancePolicyCreate(CompliancePolicyBase):
    pass

class CompliancePolicy(CompliancePolicyBase):
    id: int
    created_by_id: int

    class Config:
        from_attributes = True

class ComplianceResult(BaseModel):
    id: int
    policy_id: int
    device_id: int
    job_id: int
    ts: datetime
    status: ComplianceStatus
    details_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

from __future__ import annotations

import json
from typing import List, Optional

import yaml

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import role_required
from app.db.session import get_db
from app.devices.models import Device
from app.jobs import tasks
from app.jobs.models import Job, User
from app.jobs.service import create_job
from app.compliance.models import CompliancePolicy

router = APIRouter(prefix="/automation", tags=["automation"])


class TargetFilters(BaseModel):
    device_ids: Optional[List[int]] = None
    sites: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    vendors: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    include_disabled: bool = False


def _resolve_device_ids(db: Session, filters: TargetFilters) -> List[int]:
    query = db.query(Device)
    if filters.device_ids:
        query = query.filter(Device.id.in_(filters.device_ids))
    if filters.sites:
        query = query.filter(Device.site.in_(filters.sites))
    if filters.roles:
        query = query.filter(Device.role.in_(filters.roles))
    if filters.vendors:
        query = query.filter(Device.vendor.in_(filters.vendors))
    if filters.tags:
        for tag in filters.tags:
            query = query.filter(Device.tags.contains(tag))
    if not filters.include_disabled:
        query = query.filter(Device.enabled.is_(True))
    return [device.id for device in query.all()]


class CommandRequest(BaseModel):
    targets: TargetFilters
    commands: List[str]
    timeout_sec: Optional[int] = 60


@router.post("/commands")
def run_commands(
    request: CommandRequest,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("operator", "admin")),
):
    device_ids = _resolve_device_ids(db, request.targets)
    if not device_ids:
        raise HTTPException(status_code=400, detail="No devices matched the requested filters")
    job = create_job(db, "commands", user.id, {"device_ids": device_ids})

    tasks.enqueue_job(
        tasks.run_commands_task,
        job.id,
        device_ids,
        request.commands,
        request.timeout_sec,
    )
    return {"job_id": job.id}


class BackupRequest(BaseModel):
    targets: TargetFilters
    source: str = "manual"


@router.post("/backup")
def backup_configs(
    request: BackupRequest,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("operator", "admin")),
):
    device_ids = _resolve_device_ids(db, request.targets)
    if not device_ids:
        raise HTTPException(status_code=400, detail="No devices matched the requested filters")
    job = create_job(db, "config_backup", user.id, {"device_ids": device_ids})
    tasks.enqueue_job(tasks.backup_configs, job.id, device_ids, request.source)
    return {"job_id": job.id}


class DeployPreviewRequest(BaseModel):
    targets: TargetFilters
    snippet: str
    mode: str = "merge"


@router.post("/deploy/preview")
def deploy_preview(
    request: DeployPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("operator", "admin")),
):
    device_ids = _resolve_device_ids(db, request.targets)
    if not device_ids:
        raise HTTPException(status_code=400, detail="No devices matched the requested filters")
    job = create_job(
        db,
        "config_deploy_preview",
        user.id,
        {"device_ids": device_ids, "mode": request.mode, "snippet": request.snippet},
    )
    tasks.enqueue_job(
        tasks.preview_deploy,
        job.id,
        device_ids,
        request.snippet,
        request.mode,
    )
    return {"job_id": job.id}


class DeployCommitRequest(BaseModel):
    previous_job_id: int
    confirm: bool = False


@router.post("/deploy/commit")
def deploy_commit(
    request: DeployCommitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("operator", "admin")),
):
    preview_job = db.get(Job, request.previous_job_id)
    if not preview_job or preview_job.type != "config_deploy_preview":
        raise HTTPException(status_code=400, detail="Preview job not found")
    if preview_job.status != "success":
        raise HTTPException(status_code=400, detail="Preview job must succeed before commit")
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    payload = json.loads(preview_job.target_summary_json or "{}")
    device_ids = payload.get("device_ids", [])
    snippet = payload.get("snippet", "")
    mode = payload.get("mode", "merge")
    if not device_ids:
        raise HTTPException(status_code=400, detail="Preview job missing device targets")
    job = create_job(
        db,
        "config_deploy_commit",
        user.id,
        {"device_ids": device_ids, "snippet": snippet, "mode": mode},
    )
    tasks.enqueue_job(tasks.commit_deploy, job.id, device_ids, snippet, mode)
    return {"job_id": job.id}


class ComplianceRequest(BaseModel):
    policy_id: int
    targets: TargetFilters


@router.post("/compliance")
def run_compliance(
    request: ComplianceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(role_required("operator", "admin")),
):
    device_ids = _resolve_device_ids(db, request.targets)
    if not device_ids:
        raise HTTPException(status_code=400, detail="No devices matched the requested filters")
    policy = db.get(CompliancePolicy, request.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy_definition = yaml.safe_load(policy.definition_yaml) if policy.definition_yaml else {}
    job = create_job(
        db,
        "compliance",
        user.id,
        {"device_ids": device_ids, "policy_id": policy.id},
    )
    tasks.enqueue_job(
        tasks.compliance_task,
        job.id,
        device_ids,
        policy.id,
        policy_definition,
    )
    return {"job_id": job.id}

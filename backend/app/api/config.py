"""Configuration management API endpoints."""

import difflib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import errors
from app.core.auth import require_operator
from app.db import ConfigSnapshot, Device, get_db
from app.dependencies import get_job_service, get_operator_context, get_tenant_context
from app.domain.context import TenantRequestContext
from app.domain.exceptions import DomainError
from app.schemas.job import (
    ConfigBackupRequest,
    ConfigDeployCommitRequest,
    ConfigDeployPreviewRequest,
)
from app.services.job_service import JobService
from app.celery_app import celery_app

router = APIRouter(prefix="/config", tags=["config"])


@router.post("/backup", status_code=status.HTTP_202_ACCEPTED)
def backup_config(
    request: ConfigBackupRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Backup device configurations."""
    try:
        job = service.create_job(
            job_type="config_backup",
            user=context.user,
            customer_id=context.customer_id,
            target_summary={"filters": request.targets},
            payload={"source_label": request.source_label},
        )
    except DomainError as exc:
        raise errors.to_http(exc)

    celery_app.send_task(
        "config_backup_job",
        args=[job.id, request.targets, request.source_label],
    )
    
    return {"job_id": job.id, "status": "queued"}


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Get configuration snapshot."""
    snapshot = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )
    
    # Verify tenancy via device
    if snapshot.device.customer_id != context.customer_id:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Mask as not found
            detail="Snapshot not found",
        )
    
    return {
        "id": snapshot.id,
        "device_id": snapshot.device_id,
        "created_at": snapshot.created_at,
        "source": snapshot.source,
        "config_text": snapshot.config_text,
        "hash": snapshot.hash,
    }


@router.post("/deploy/preview", status_code=status.HTTP_202_ACCEPTED)
def deploy_config_preview(
    request: ConfigDeployPreviewRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Preview configuration deployment."""
    # Create job
    try:
        job = service.create_job(
            job_type="config_deploy_preview",
            user=context.user,
            customer_id=context.customer_id,
            target_summary={"filters": request.targets},
            payload={
                "mode": request.mode,
                "snippet": request.snippet,
            },
        )
    except DomainError as exc:
        raise errors.to_http(exc)
    
    # Enqueue Celery task
    celery_app.send_task(
        "config_deploy_preview_job",
        args=[job.id, request.targets, request.mode, request.snippet],
    )
    
    return {"job_id": job.id, "status": "queued"}


@router.post("/deploy/commit", status_code=status.HTTP_202_ACCEPTED)
def deploy_config_commit(
    request: ConfigDeployCommitRequest,
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Commit configuration deployment."""
    # Get previous preview job
    try:
        preview_job = service.get_job(request.previous_job_id, context)
    except DomainError as exc:
        raise errors.to_http(exc)
    
    if preview_job.type != "config_deploy_preview":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced job is not a preview job",
        )
    
    if preview_job.status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview job must be successful before committing",
        )
    
    # Get payload from preview job
    payload = preview_job.payload_json
    targets = preview_job.target_summary_json["filters"]
    
    # Create commit job
    try:
        job = service.create_job(
            job_type="config_deploy_commit",
            user=context.user,
            customer_id=context.customer_id,
            target_summary={"filters": targets, "preview_job_id": request.previous_job_id},
            payload=payload,
        )
    except DomainError as exc:
        raise errors.to_http(exc)
    
    # Enqueue Celery task
    celery_app.send_task(
        "config_deploy_commit_job",
        args=[job.id, targets, payload["mode"], payload["snippet"]],
    )
    
    return {"job_id": job.id, "status": "queued"}


# Device-specific endpoints
@router.get("/devices/{device_id}/snapshots")
def list_device_snapshots(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[dict]:
    """List configuration snapshots for a device."""
    device = (
        db.query(Device)
        .filter(
            Device.id == device_id,
            Device.customer_id == context.customer_id,
        )
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    snapshots = (
        db.query(ConfigSnapshot)
        .filter(ConfigSnapshot.device_id == device_id)
        .order_by(ConfigSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "source": s.source,
            "hash": s.hash,
            "job_id": s.job_id,
        }
        for s in snapshots
    ]


@router.get("/devices/{device_id}/diff")
def get_config_diff(
    device_id: int,
    from_snapshot: int = Query(..., alias="from"),
    to_snapshot: int = Query(..., alias="to"),
    db: Session = Depends(get_db),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Get diff between two configuration snapshots."""
    device = (
        db.query(Device)
        .filter(
            Device.id == device_id,
            Device.customer_id == context.customer_id,
        )
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    snapshot_from = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == from_snapshot).first()
    snapshot_to = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == to_snapshot).first()
    
    if not snapshot_from or not snapshot_to:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both snapshots not found",
        )
    
    if snapshot_from.device_id != device_id or snapshot_to.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Snapshots must belong to the specified device",
        )
    
    # Generate diff
    from_lines = snapshot_from.config_text.splitlines(keepends=True)
    to_lines = snapshot_to.config_text.splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        from_lines,
        to_lines,
        fromfile=f"Snapshot {from_snapshot}",
        tofile=f"Snapshot {to_snapshot}",
    ))
    
    return {
        "device_id": device_id,
        "from_snapshot": from_snapshot,
        "to_snapshot": to_snapshot,
        "diff": "".join(diff),
    }

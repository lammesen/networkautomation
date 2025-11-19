from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import difflib

from app import schemas
from app.crud import job as crud_job
from app.db.session import get_db
from app.api.auth import require_role
from app.db.models import UserRole, JobType, ConfigSnapshot
from app.jobs.config_backup import config_backup_job
from app.jobs.config_deploy import config_deploy_preview_job, config_deploy_commit_job
from app.crud.device import get_device

router = APIRouter()


@router.post("/backup", response_model=schemas.job.Job)
def backup_configurations(
    backup_request: schemas.config_backup.ConfigBackupRequest,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    job = crud_job.create_job(
        db,
        schemas.job.JobCreate(
            type=JobType.config_backup,
            target_summary_json=backup_request.targets,
        ),
        current_user,
    )
    config_backup_job.delay(
        job_id=job.id,
        targets=backup_request.targets,
        source_label=backup_request.source_label,
    )
    return job


@router.get("/snapshots/{snapshot_id}", response_model=str)
def get_snapshot_config(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    snapshot = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    # TODO: Add authorization check to ensure user can view this device's config
    return snapshot.config_text


@router.get("/devices/{device_id}/snapshots", response_model=list[schemas.config_backup.ConfigSnapshot])
def get_device_snapshots(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    device = get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    # TODO: Auth check
    return db.query(ConfigSnapshot).filter(ConfigSnapshot.device_id == device_id).order_by(ConfigSnapshot.created_at.desc()).all()


@router.get("/devices/{device_id}/diff", response_model=str)
def get_config_diff(
    device_id: int,
    from_snap_id: int,
    to_snap_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    from_snap = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == from_snap_id, ConfigSnapshot.device_id == device_id).first()
    to_snap = db.query(ConfigSnapshot).filter(ConfigSnapshot.id == to_snap_id, ConfigSnapshot.device_id == device_id).first()

    if not from_snap or not to_snap:
        raise HTTPException(status_code=404, detail="One or both snapshots not found for this device")

    diff = difflib.unified_diff(
        from_snap.config_text.splitlines(keepends=True),
        to_snap.config_text.splitlines(keepends=True),
        fromfile=f"snapshot_{from_snap_id}",
        tofile=f"snapshot_{to_snap_id}",
    )
    return "".join(diff)


@router.post("/deploy/preview", response_model=schemas.job.Job)
def preview_config_deployment(
    deploy_request: schemas.config_deploy.ConfigDeployPreviewRequest,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    job = crud_job.create_job(
        db,
        schemas.job.JobCreate(
            type=JobType.config_deploy_preview,
            target_summary_json=deploy_request.targets,
        ),
        current_user,
    )
    config_deploy_preview_job.delay(
        job_id=job.id,
        targets=deploy_request.targets,
        snippet=deploy_request.snippet,
    )
    return job


@router.post("/deploy/commit", response_model=schemas.job.Job)
def commit_config_deployment(
    commit_request: schemas.config_deploy.ConfigDeployCommitRequest,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    preview_job = crud_job.get_job(db, commit_request.previous_job_id)
    if not preview_job or preview_job.type != JobType.config_deploy_preview or preview_job.status != JobStatus.success:
        raise HTTPException(status_code=400, detail="A valid and successful preview job is required.")

    job = crud_job.create_job(
        db,
        schemas.job.JobCreate(
            type=JobType.config_deploy_commit,
            target_summary_json=preview_job.target_summary_json,
        ),
        current_user,
    )
    config_deploy_commit_job.delay(
        job_id=job.id,
        preview_job_id=commit_request.previous_job_id,
    )
    return job

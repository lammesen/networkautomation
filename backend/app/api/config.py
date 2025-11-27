"""Configuration management API endpoints."""

from fastapi import APIRouter, Depends, Query, Request, status

from app.celery_app import celery_app
from app.core.audit import AuditAction, AuditOutcome, audit_log
from app.dependencies import (
    get_config_service,
    get_job_service,
    get_multi_tenant_context,
    get_operator_context,
    get_tenant_context,
)
from app.domain.context import MultiTenantContext, TenantRequestContext
from app.schemas.job import (
    ConfigBackupRequest,
    ConfigDeployCommitRequest,
    ConfigDeployPreviewRequest,
    ConfigRollbackCommitRequest,
    ConfigRollbackPreviewRequest,
)
from app.services.config_service import ConfigService
from app.services.job_service import JobService

router = APIRouter(prefix="/config", tags=["config"])


def _get_ip_address(request: Request) -> str | None:
    """Extract client IP address from request."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/backup", status_code=status.HTTP_202_ACCEPTED)
def backup_config(
    http_request: Request,
    request: ConfigBackupRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Backup device configurations."""
    job = service.create_job(
        job_type="config_backup",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={"filters": request.targets},
        payload={"source_label": request.source_label},
    )

    celery_app.send_task(
        "config_backup_job",
        args=[job.id, request.targets, request.source_label],
    )

    audit_log(
        AuditAction.CONFIG_BACKUP,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(http_request),
        user_agent=http_request.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "config_backup",
            "targets": request.targets,
            "source_label": request.source_label,
        },
    )

    return {"job_id": job.id, "status": "queued"}


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: int,
    config_service: ConfigService = Depends(get_config_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> dict:
    """Get configuration snapshot."""
    snapshot = config_service.get_snapshot_multi_tenant(snapshot_id, context)

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
    http_request: Request,
    request: ConfigDeployPreviewRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Preview configuration deployment."""
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

    celery_app.send_task(
        "config_deploy_preview_job",
        args=[job.id, request.targets, request.mode, request.snippet],
    )

    audit_log(
        AuditAction.CONFIG_DEPLOY_PREVIEW,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(http_request),
        user_agent=http_request.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "config_deploy_preview",
            "targets": request.targets,
            "mode": request.mode,
            "snippet_length": len(request.snippet) if request.snippet else 0,
        },
    )

    return {"job_id": job.id, "status": "queued"}


@router.post("/deploy/commit", status_code=status.HTTP_202_ACCEPTED)
def deploy_config_commit(
    http_request: Request,
    request: ConfigDeployCommitRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Commit configuration deployment."""
    from app.domain.exceptions import ValidationError

    preview_job = service.get_job(request.previous_job_id, context)

    if preview_job.type != "config_deploy_preview":
        raise ValidationError("Referenced job is not a preview job")

    if preview_job.status != "success":
        raise ValidationError("Preview job must be successful before committing")

    payload = preview_job.payload_json
    targets = preview_job.target_summary_json["filters"]

    job = service.create_job(
        job_type="config_deploy_commit",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={"filters": targets, "preview_job_id": request.previous_job_id},
        payload=payload,
    )

    celery_app.send_task(
        "config_deploy_commit_job",
        args=[job.id, targets, payload["mode"], payload["snippet"]],
    )

    audit_log(
        AuditAction.CONFIG_DEPLOY_COMMIT,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(http_request),
        user_agent=http_request.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "config_deploy_commit",
            "preview_job_id": request.previous_job_id,
            "targets": targets,
            "mode": payload.get("mode"),
        },
    )

    return {"job_id": job.id, "status": "queued"}


# Device-specific endpoints
@router.get("/devices/{device_id}/snapshots")
def list_device_snapshots(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    config_service: ConfigService = Depends(get_config_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> list[dict]:
    """List configuration snapshots for a device."""
    snapshots = config_service.list_device_snapshots_multi_tenant(device_id, context, limit=limit)

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
    config_service: ConfigService = Depends(get_config_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> dict:
    """Get diff between two configuration snapshots."""
    return config_service.get_config_diff_multi_tenant(
        device_id, from_snapshot, to_snapshot, context
    )


@router.post("/rollback/preview", status_code=status.HTTP_202_ACCEPTED)
def rollback_config_preview(
    http_request: Request,
    request: ConfigRollbackPreviewRequest,
    config_service: ConfigService = Depends(get_config_service),
    job_service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Preview configuration rollback to a previous snapshot.

    This compares the target snapshot with the device's current running config
    and shows what would change if the rollback is applied.
    """
    # Verify snapshot exists and user has access
    snapshot = config_service.get_snapshot(request.snapshot_id, context)

    job = job_service.create_job(
        job_type="config_rollback_preview",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={
            "snapshot_id": snapshot.id,
            "device_id": snapshot.device_id,
        },
        payload={
            "snapshot_id": snapshot.id,
            "config_text": snapshot.config_text,
        },
    )

    celery_app.send_task(
        "config_rollback_preview_job",
        args=[job.id, snapshot.device_id, snapshot.config_text],
    )

    audit_log(
        AuditAction.CONFIG_ROLLBACK_PREVIEW,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(http_request),
        user_agent=http_request.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "config_rollback_preview",
            "snapshot_id": snapshot.id,
            "device_id": snapshot.device_id,
        },
    )

    return {"job_id": job.id, "status": "queued"}


@router.post("/rollback/commit", status_code=status.HTTP_202_ACCEPTED)
def rollback_config_commit(
    http_request: Request,
    request: ConfigRollbackCommitRequest,
    job_service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Commit configuration rollback after previewing.

    Requires a successful rollback preview job first.
    """
    from app.domain.exceptions import ValidationError

    preview_job = job_service.get_job(request.previous_job_id, context)

    if preview_job.type != "config_rollback_preview":
        raise ValidationError("Referenced job is not a rollback preview job")

    if preview_job.status != "success":
        raise ValidationError("Preview job must be successful before committing")

    if not request.confirm:
        raise ValidationError("Confirmation required to commit rollback")

    payload = preview_job.payload_json
    target_summary = preview_job.target_summary_json

    job = job_service.create_job(
        job_type="config_rollback_commit",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={
            **target_summary,
            "preview_job_id": request.previous_job_id,
        },
        payload=payload,
    )

    celery_app.send_task(
        "config_rollback_commit_job",
        args=[job.id, target_summary["device_id"], payload["config_text"]],
    )

    audit_log(
        AuditAction.CONFIG_ROLLBACK_COMMIT,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(http_request),
        user_agent=http_request.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "config_rollback_commit",
            "preview_job_id": request.previous_job_id,
            "snapshot_id": target_summary.get("snapshot_id"),
            "device_id": target_summary.get("device_id"),
        },
    )

    return {"job_id": job.id, "status": "queued"}

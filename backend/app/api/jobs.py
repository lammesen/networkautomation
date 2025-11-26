"""Job API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_admin_user, get_job_service, get_tenant_context
from app.domain.context import TenantRequestContext
from app.domain.jobs import JobFilters
from app.schemas.job import JobLogResponse, JobResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
admin_router = APIRouter(prefix="/jobs/admin", tags=["jobs-admin"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    job_type: Optional[str] = Query(None, alias="type"),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[JobResponse]:
    """List jobs for the active customer with optional filters."""
    filters = JobFilters(job_type=job_type, status=status, skip=skip, limit=limit)
    jobs = service.list_jobs(filters, context)
    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> JobResponse:
    """Get job details."""
    job = service.get_job(job_id, context)
    return JobResponse.model_validate(job)


@router.get("/{job_id}/logs", response_model=list[JobLogResponse])
def get_job_logs_endpoint(
    job_id: int,
    limit: int = Query(1000, ge=1, le=10000),
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[JobLogResponse]:
    """Get job logs."""
    logs = service.get_job_logs(job_id, limit=limit, context=context)
    return [JobLogResponse.model_validate(log) for log in logs]


@router.get("/{job_id}/results")
def get_job_results(
    job_id: int,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Get job results from result_summary_json."""
    job = service.get_job(job_id, context)
    return {
        "job_id": job.id,
        "status": job.status,
        "results": job.result_summary_json or {},
    }


@router.post("/{job_id}/retry")
def retry_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Retry a failed or stuck job by creating a new job with the same payload."""
    job = service.get_job(job_id, context)
    new_job = service.retry_job(job, context.user)
    return {"job_id": new_job.id, "status": new_job.status}


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Cancel a scheduled or queued job."""
    job = service.cancel_job(job_id, context)
    return {"job_id": job.id, "status": job.status}


# ---------------- Admin-only endpoints ----------------


@admin_router.get("", response_model=list[JobResponse])
def list_jobs_admin(
    job_type: Optional[str] = Query(None, alias="type"),
    status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: JobService = Depends(get_job_service),
    _: object = Depends(get_admin_user),
) -> list[JobResponse]:
    filters = JobFilters(job_type=job_type, status=status, skip=skip, limit=limit)
    jobs = service.list_jobs_admin(filters, customer_id=customer_id, user_id=user_id)
    return [JobResponse.model_validate(job) for job in jobs]


@admin_router.get("/{job_id}", response_model=JobResponse)
def get_job_admin(
    job_id: int,
    service: JobService = Depends(get_job_service),
    _: object = Depends(get_admin_user),
) -> JobResponse:
    job = service.get_job_admin(job_id)
    return JobResponse.model_validate(job)


@admin_router.get("/{job_id}/logs", response_model=list[JobLogResponse])
def get_job_logs_admin(
    job_id: int,
    limit: int = Query(1000, ge=1, le=10000),
    service: JobService = Depends(get_job_service),
    _: object = Depends(get_admin_user),
) -> list[JobLogResponse]:
    logs = service.get_job_logs_admin(job_id, limit=limit)
    return [JobLogResponse.model_validate(log) for log in logs]

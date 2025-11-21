"""Job API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api import errors
from app.dependencies import get_job_service, get_tenant_context
from app.domain.context import TenantRequestContext
from app.domain.exceptions import DomainError
from app.domain.jobs import JobFilters
from app.schemas.job import JobLogResponse, JobResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _handle_error(exc: DomainError):
    raise errors.to_http(exc)


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
    try:
        job = service.get_job(job_id, context)
        return JobResponse.model_validate(job)
    except DomainError as exc:
        _handle_error(exc)


@router.get("/{job_id}/logs", response_model=list[JobLogResponse])
def get_job_logs_endpoint(
    job_id: int,
    limit: int = Query(1000, ge=1, le=10000),
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[JobLogResponse]:
    """Get job logs."""
    try:
        logs = service.get_job_logs(job_id, limit=limit, context=context)
        return [JobLogResponse.model_validate(log) for log in logs]
    except DomainError as exc:
        _handle_error(exc)


@router.get("/{job_id}/results")
def get_job_results(
    job_id: int,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> dict:
    """Get job results from result_summary_json."""
    try:
        job = service.get_job(job_id, context)
        return {
            "job_id": job.id,
            "status": job.status,
            "results": job.result_summary_json or {},
        }
    except DomainError as exc:
        _handle_error(exc)

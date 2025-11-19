"""Job API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.auth import get_current_user
from app.db import get_db, Job, User
from app.schemas.job import JobResponse, JobLogResponse
from app.jobs.manager import get_job_logs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    job_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobResponse]:
    """List jobs with optional filters."""
    query = db.query(Job)
    
    if job_type:
        query = query.filter(Job.type == job_type)
    
    if status:
        query = query.filter(Job.status == status)
    
    # Non-admin users only see their own jobs
    if current_user.role != "admin":
        query = query.filter(Job.user_id == current_user.id)
    
    jobs = query.order_by(Job.requested_at.desc()).offset(skip).limit(limit).all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Get job details."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Non-admin users can only view their own jobs
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return JobResponse.model_validate(job)


@router.get("/{job_id}/logs", response_model=list[JobLogResponse])
def get_job_logs_endpoint(
    job_id: int,
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobLogResponse]:
    """Get job logs."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Non-admin users can only view their own job logs
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    logs = get_job_logs(db, job_id, limit)
    return [JobLogResponse.model_validate(log) for log in logs]


@router.get("/{job_id}/results")
def get_job_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get job results from result_summary_json."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Non-admin users can only view their own job results
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "results": job.result_summary_json or {},
    }

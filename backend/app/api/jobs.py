from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import job as crud_job
from app.db.session import get_db
from app.api.auth import get_current_user
from app.db.models import JobType, JobStatus
from app.jobs.tasks import run_job

router = APIRouter()


@router.get("/", response_model=List[schemas.job.Job])
def read_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(get_current_user),
):
    return crud_job.get_jobs(
        db, skip=skip, limit=limit, status=status, job_type=job_type, user_id=current_user.id
    )


@router.get("/{job_id}", response_model=schemas.job.Job)
def read_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(get_current_user),
):
    db_job = crud_job.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    return db_job


@router.get("/{job_id}/logs", response_model=List[schemas.job.JobLog])
def read_job_logs(
    job_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(get_current_user),
):
    db_job = crud_job.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job's logs")
    return crud_job.get_job_logs(db, job_id=job_id, skip=skip, limit=limit)


@router.post("/test", response_model=schemas.job.Job)
def test_job(
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(get_current_user),
):
    job = crud_job.create_job(db, schemas.job.JobCreate(type=JobType.run_commands), current_user)
    run_job.delay(job.id)
    return job

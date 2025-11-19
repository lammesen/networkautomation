"""Job management utilities."""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.db import Job, JobLog, User
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_job(
    db: Session,
    job_type: str,
    user: User,
    target_summary: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> Job:
    """Create a new job in the database."""
    job = Job(
        type=job_type,
        status="queued",
        user_id=user.id,
        target_summary_json=target_summary,
        payload_json=payload,
        requested_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"Created job {job.id} of type {job_type} for user {user.username}")
    return job


def update_job_status(
    db: Session,
    job_id: int,
    status: str,
    result_summary: Optional[dict] = None,
) -> None:
    """Update job status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    job.status = status
    
    if status == "running" and not job.started_at:
        job.started_at = datetime.utcnow()
    
    if status in ["success", "partial", "failed"]:
        job.finished_at = datetime.utcnow()
    
    if result_summary:
        job.result_summary_json = result_summary
    
    db.commit()
    logger.info(f"Updated job {job_id} status to {status}")


def create_job_log(
    db: Session,
    job_id: int,
    level: str,
    message: str,
    host: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Create a job log entry."""
    log = JobLog(
        job_id=job_id,
        ts=datetime.utcnow(),
        level=level,
        host=host,
        message=message,
        extra_json=extra,
    )
    db.add(log)
    db.commit()


def get_job_logs(db: Session, job_id: int, limit: int = 1000) -> list[JobLog]:
    """Get job logs."""
    return (
        db.query(JobLog)
        .filter(JobLog.job_id == job_id)
        .order_by(JobLog.ts.asc())
        .limit(limit)
        .all()
    )

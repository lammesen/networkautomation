"""Job management utilities."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import Job, JobLog, User
from app.domain.exceptions import DomainError
from app.services.job_service import JobService

logger = get_logger(__name__)


def _service(db: Session) -> JobService:
    return JobService(db)


def create_job(
    db: Session,
    job_type: str,
    user: User,
    customer_id: int,
    target_summary: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> Job:
    """Create a new job in the database."""
    job = _service(db).create_job(
        job_type=job_type,
        user=user,
        customer_id=customer_id,
        target_summary=target_summary,
        payload=payload,
    )
    logger.info(
        "Created job %s of type %s for user %s (customer %s)",
        job.id,
        job_type,
        user.username,
        customer_id,
    )
    return job


def update_job_status(
    db: Session,
    job_id: int,
    status: str,
    result_summary: Optional[dict] = None,
) -> None:
    """Update job status."""
    try:
        _service(db).set_status(job_id, status, result_summary)
        logger.info("Updated job %s status to %s", job_id, status)
    except DomainError as exc:
        logger.error("Failed to update job %s: %s", job_id, exc)


def create_job_log(
    db: Session,
    job_id: int,
    level: str,
    message: str,
    host: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Create a job log entry."""
    try:
        _service(db).append_log(
            job_id,
            level=level,
            message=message,
            host=host,
            extra=extra,
        )
    except DomainError as exc:  # pragma: no cover - logging safeguard
        logger.error("Failed to append log for job %s: %s", job_id, exc)


def get_job_logs(db: Session, job_id: int, limit: int = 1000) -> list[JobLog]:
    """Get job logs."""
    return JobService(db).logs.list_for_job(job_id, limit=limit)

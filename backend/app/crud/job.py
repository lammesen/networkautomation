import redis
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.db.models import Job, JobLog, JobType, JobStatus, User
from app.schemas.job import JobCreate

r = redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)


def get_job(db: Session, job_id: int) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id).first()


def get_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    user_id: Optional[int] = None,
) -> List[Job]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.type == job_type)
    if user_id:
        query = query.filter(Job.user_id == user_id)
    return query.order_by(Job.id.desc()).offset(skip).limit(limit).all()


def create_job(db: Session, job: JobCreate, user: User) -> Job:
    db_job = Job(**job.model_dump(), user_id=user.id)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def update_job_status(db: Session, db_job: Job, status: JobStatus) -> Job:
    db_job.status = status
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def create_job_log_and_publish(db: Session, job_id: int, level: str, message: str, host: Optional[str] = None, extra: Optional[dict] = None) -> JobLog:
    db_log = JobLog(job_id=job_id, level=level, message=message, host=host, extra_json=extra)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    log_data = {
        "ts": db_log.ts.isoformat(),
        "level": level,
        "message": message,
        "host": host,
        "extra": extra,
    }
    r.publish(f"job_{job_id}", json.dumps(log_data))

    return db_log


def get_job_logs(db: Session, job_id: int, skip: int = 0, limit: int = 1000) -> List[JobLog]:
    return db.query(JobLog).filter(JobLog.job_id == job_id).order_by(JobLog.ts.asc()).offset(skip).limit(limit).all()

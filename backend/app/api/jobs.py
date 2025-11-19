from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.jobs.models import Job, JobLog

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_user)],
)


def _serialize_job(job: Job) -> dict:
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "requested_at": job.requested_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "target_summary": json.loads(job.target_summary_json or "{}"),
        "result_summary": json.loads(job.result_summary_json or "{}"),
    }


@router.get("", response_model=List[dict])
def list_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
):
    query = db.query(Job).order_by(Job.requested_at.desc())
    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.type == job_type)
    return [_serialize_job(job) for job in query.all()]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404)
    return _serialize_job(job)


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
):
    logs = (
        db.query(JobLog)
        .filter(JobLog.job_id == job_id)
        .order_by(JobLog.ts)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "ts": log.ts,
            "level": log.level,
            "message": log.message,
            "host": log.host,
            "extra": json.loads(log.extra_json or "{}"),
        }
        for log in logs
    ]


@router.get("/{job_id}/results")
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404)
    return json.loads(job.result_summary_json or "{}")

"""Job orchestration services."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import Job, JobLog, User
from app.domain.context import TenantRequestContext
from app.domain.exceptions import ForbiddenError, NotFoundError
from app.domain.jobs import JobFilters
from app.repositories import JobLogRepository, JobRepository


class JobService:
    """Coordinates job lifecycle and querying."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.jobs = JobRepository(session)
        self.logs = JobLogRepository(session)

    # ------------------------------------------------------------------
    # Creation & updates

    def create_job(
        self,
        *,
        job_type: str,
        user: User,
        customer_id: int,
        target_summary: Optional[dict] = None,
        payload: Optional[dict] = None,
    ) -> Job:
        job = Job(
            type=job_type,
            status="queued",
            user_id=user.id,
            customer_id=customer_id,
            target_summary_json=target_summary,
            payload_json=payload,
            requested_at=datetime.utcnow(),
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def set_status(
        self,
        job_id: int,
        status: str,
        result_summary: Optional[dict] = None,
    ) -> None:
        job = self.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found")

        job.status = status
        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in {"success", "partial", "failed"}:
            job.finished_at = datetime.utcnow()
        if result_summary is not None:
            job.result_summary_json = result_summary

        self.session.commit()

    def append_log(
        self,
        job_id: int,
        *,
        level: str,
        message: str,
        host: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> JobLog:
        job = self.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found")

        log = JobLog(
            job_id=job_id,
            ts=datetime.utcnow(),
            level=level,
            host=host,
            message=message,
            extra_json=extra,
        )
        self.session.add(log)
        self.session.commit()
        return log

    # ------------------------------------------------------------------
    # Queries

    def list_jobs(
        self,
        filters: JobFilters,
        context: TenantRequestContext,
    ) -> Sequence[Job]:
        return self.jobs.list_for_customer(
            context.customer_id,
            job_type=filters.job_type,
            status=filters.status,
            skip=filters.skip,
            limit=filters.limit,
        )

    def get_job(self, job_id: int, context: TenantRequestContext) -> Job:
        job = self.jobs.get_by_id(job_id)
        if not job or job.customer_id != context.customer_id:
            raise NotFoundError("Job not found")
        return job

    def get_job_logs(
        self,
        job_id: int,
        *,
        limit: int,
        context: TenantRequestContext,
    ) -> Sequence[JobLog]:
        job = self.get_job(job_id, context)
        return self.logs.list_for_job(job.id, limit=limit)



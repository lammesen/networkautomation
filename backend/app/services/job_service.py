"""Job orchestration services."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import Job, JobLog, User
from app.domain.context import MultiTenantContext, TenantRequestContext
from app.domain.exceptions import NotFoundError
from app.domain.jobs import JobFilters
from app.repositories import JobLogRepository, JobRepository
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


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
        scheduled_for: Optional[datetime] = None,
    ) -> Job:
        status = "queued"
        now = datetime.utcnow()
        if scheduled_for and scheduled_for > now:
            status = "scheduled"
        scheduled_at = scheduled_for if scheduled_for else None

        job = Job(
            type=job_type,
            status=status,
            user_id=user.id,
            customer_id=customer_id,
            target_summary_json=target_summary,
            payload_json=payload,
            requested_at=now,
            scheduled_for=scheduled_at,
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

    def list_jobs_multi_tenant(
        self,
        filters: JobFilters,
        context: MultiTenantContext,
    ) -> Sequence[Job]:
        """List jobs across all accessible customers."""
        return self.jobs.list_for_customers(
            context.customer_ids,
            job_type=filters.job_type,
            status=filters.status,
            skip=filters.skip,
            limit=filters.limit,
        )

    def list_jobs_for_device(
        self,
        hostname: str,
        filters: JobFilters,
        context: TenantRequestContext,
    ) -> Sequence[Job]:
        """List jobs that targeted a specific device."""
        return self.jobs.list_for_device(
            context.customer_id,
            hostname,
            job_type=filters.job_type,
            status=filters.status,
            skip=filters.skip,
            limit=filters.limit,
        )

    def list_jobs_for_device_multi_tenant(
        self,
        hostname: str,
        filters: JobFilters,
        context: MultiTenantContext,
    ) -> Sequence[Job]:
        """List jobs that targeted a specific device across accessible customers."""
        return self.jobs.list_for_device_multi_customer(
            context.customer_ids,
            hostname,
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

    def get_job_multi_tenant(self, job_id: int, context: MultiTenantContext) -> Job:
        """Get a job if it belongs to any accessible customer."""
        job = self.jobs.get_by_id_for_customers(job_id, context.customer_ids)
        if not job:
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

    def get_job_logs_multi_tenant(
        self,
        job_id: int,
        *,
        limit: int,
        context: MultiTenantContext,
    ) -> Sequence[JobLog]:
        """Get job logs if job belongs to any accessible customer."""
        job = self.get_job_multi_tenant(job_id, context)
        return self.logs.list_for_job(job.id, limit=limit)

    def cancel_job_multi_tenant(self, job_id: int, context: MultiTenantContext) -> Job:
        """Cancel a scheduled or queued job (multi-tenant version)."""
        from app.domain.exceptions import ValidationError

        job = self.get_job_multi_tenant(job_id, context)

        if job.status not in ("scheduled", "queued"):
            raise ValidationError(
                f"Cannot cancel job with status '{job.status}'. "
                "Only 'scheduled' or 'queued' jobs can be cancelled."
            )

        job.status = "cancelled"
        job.finished_at = datetime.utcnow()
        self.session.commit()

        self.append_log(
            job_id,
            level="INFO",
            message=f"Job cancelled by user {context.user.id}",
        )

        return job

    def retry_job(self, job: Job, user: User) -> Job:
        """Create a new job based on an existing one (for retry)."""
        clone = Job(
            type=job.type,
            status="queued",
            user_id=user.id,
            customer_id=job.customer_id,
            target_summary_json=job.target_summary_json,
            payload_json=job.payload_json,
            requested_at=datetime.utcnow(),
        )
        self.session.add(clone)
        self.session.commit()
        self.session.refresh(clone)
        self._enqueue(clone)
        return clone

    def cancel_job(self, job_id: int, context: TenantRequestContext) -> Job:
        """Cancel a scheduled or queued job."""
        from app.domain.exceptions import ValidationError

        job = self.get_job(job_id, context)

        if job.status not in ("scheduled", "queued"):
            raise ValidationError(
                f"Cannot cancel job with status '{job.status}'. Only 'scheduled' or 'queued' jobs can be cancelled."
            )

        job.status = "cancelled"
        job.finished_at = datetime.utcnow()
        self.session.commit()

        # Log the cancellation
        self.append_log(
            job_id,
            level="INFO",
            message=f"Job cancelled by user {context.user.id}",
        )

        return job

    # Internal ------------------------------------------------------
    def _enqueue(self, job: Job) -> None:
        """Dispatch job to Celery based on its type."""
        task_map = {
            "run_commands": (
                "run_commands_job",
                lambda j: (
                    j.id,
                    j.target_summary_json["filters"],
                    j.payload_json["commands"],
                    j.payload_json.get("timeout"),
                ),
            ),
            "config_backup": (
                "config_backup_job",
                lambda j: (
                    j.id,
                    j.target_summary_json.get("filters", {}),
                    j.payload_json.get("source_label", "manual"),
                ),
            ),
            "config_deploy_preview": (
                "config_deploy_preview_job",
                lambda j: (
                    j.id,
                    j.target_summary_json["filters"],
                    j.payload_json["mode"],
                    j.payload_json["snippet"],
                ),
            ),
            "config_deploy_commit": (
                "config_deploy_commit_job",
                lambda j: (
                    j.id,
                    j.target_summary_json["filters"],
                    j.payload_json["mode"],
                    j.payload_json["snippet"],
                ),
            ),
            "compliance_check": (
                "compliance_check_job",
                lambda j: (j.id, j.payload_json["policy_id"]),
            ),
        }
        entry = task_map.get(job.type)
        if not entry:
            return
        task_name, args_fn = entry
        try:
            celery_app.send_task(task_name, args=args_fn(job))
        except Exception as exc:
            logger.warning("Failed to enqueue job %s: %s", job.id, exc)

    # ---------------- Admin (global) ----------------
    def list_jobs_admin(
        self,
        filters: JobFilters,
        customer_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Sequence[Job]:
        return self.jobs.list_all(
            job_type=filters.job_type,
            status=filters.status,
            customer_id=customer_id,
            user_id=user_id,
            skip=filters.skip,
            limit=filters.limit,
        )

    def get_job_admin(self, job_id: int) -> Job:
        job = self.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError("Job not found")
        return job

    def get_job_logs_admin(self, job_id: int, *, limit: int) -> Sequence[JobLog]:
        job = self.get_job_admin(job_id)
        return self.logs.list_for_job(job.id, limit=limit)

"""Job persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import cast, String
from sqlalchemy.orm import Session  # type: ignore[import]

from app.db import Job, JobLog
from app.repositories.base import SQLAlchemyRepository


class JobRepository(SQLAlchemyRepository[Job]):
    """Encapsulates job queries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_id(self, job_id: int) -> Optional[Job]:
        return self.session.query(Job).filter(Job.id == job_id).first()

    def list_for_customer(
        self,
        customer_id: int,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Job]:
        query = (
            self.session.query(Job)
            .filter(Job.customer_id == customer_id)
            .order_by(Job.requested_at.desc())
        )
        if job_type:
            query = query.filter(Job.type == job_type)
        if status:
            query = query.filter(Job.status == status)
        return query.offset(skip).limit(min(limit, 1000)).all()

    def list_for_device(
        self,
        customer_id: int,
        hostname: str,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Job]:
        """List jobs that targeted a specific device hostname.

        Searches for the hostname in the target_summary_json field.
        Uses a text search since target_summary_json has varied structures.
        """
        query = (
            self.session.query(Job)
            .filter(Job.customer_id == customer_id)
            .filter(cast(Job.target_summary_json, String).contains(f'"{hostname}"'))
            .order_by(Job.requested_at.desc())
        )
        if job_type:
            query = query.filter(Job.type == job_type)
        if status:
            query = query.filter(Job.status == status)
        return query.offset(skip).limit(min(limit, 1000)).all()

    def list_for_device_multi_customer(
        self,
        customer_ids: Sequence[int],
        hostname: str,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Job]:
        """List jobs that targeted a specific device hostname across multiple customers."""
        query = (
            self.session.query(Job)
            .filter(Job.customer_id.in_(customer_ids))
            .filter(cast(Job.target_summary_json, String).contains(f'"{hostname}"'))
            .order_by(Job.requested_at.desc())
        )
        if job_type:
            query = query.filter(Job.type == job_type)
        if status:
            query = query.filter(Job.status == status)
        return query.offset(skip).limit(min(limit, 1000)).all()

    def list_for_customers(
        self,
        customer_ids: Sequence[int],
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Job]:
        """List jobs for multiple customers."""
        query = (
            self.session.query(Job)
            .filter(Job.customer_id.in_(customer_ids))
            .order_by(Job.requested_at.desc())
        )
        if job_type:
            query = query.filter(Job.type == job_type)
        if status:
            query = query.filter(Job.status == status)
        return query.offset(skip).limit(min(limit, 1000)).all()

    def get_by_id_for_customers(
        self,
        job_id: int,
        customer_ids: Sequence[int],
    ) -> Optional[Job]:
        """Get a job if it belongs to any of the specified customers."""
        return (
            self.session.query(Job)
            .filter(Job.id == job_id)
            .filter(Job.customer_id.in_(customer_ids))
            .first()
        )

    def list_all(
        self,
        *,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Job]:
        query = self.session.query(Job).order_by(Job.requested_at.desc())
        if job_type:
            query = query.filter(Job.type == job_type)
        if status:
            query = query.filter(Job.status == status)
        if customer_id:
            query = query.filter(Job.customer_id == customer_id)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        return query.offset(skip).limit(min(limit, 1000)).all()


class JobLogRepository(SQLAlchemyRepository[JobLog]):
    """Encapsulates job log queries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_job(self, job_id: int, limit: int = 1000) -> Sequence[JobLog]:
        return (
            self.session.query(JobLog)
            .filter(JobLog.job_id == job_id)
            .order_by(JobLog.ts.asc())
            .limit(limit)
            .all()
        )

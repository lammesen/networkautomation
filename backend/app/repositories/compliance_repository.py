"""Compliance persistence helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db import CompliancePolicy, ComplianceResult, Device
from app.repositories.base import SQLAlchemyRepository


class CompliancePolicyRepository(SQLAlchemyRepository[CompliancePolicy]):
    """Encapsulates all direct CompliancePolicy ORM access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def _customer_query(self, customer_id: int):
        return self.session.query(CompliancePolicy).filter(
            CompliancePolicy.customer_id == customer_id
        )

    def _customers_query(self, customer_ids: Sequence[int]):
        return self.session.query(CompliancePolicy).filter(
            CompliancePolicy.customer_id.in_(customer_ids)
        )

    def get_by_id(self, policy_id: int) -> Optional[CompliancePolicy]:
        return self.session.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()

    def get_by_id_for_customer(
        self, policy_id: int, customer_id: int
    ) -> Optional[CompliancePolicy]:
        return self._customer_query(customer_id).filter(CompliancePolicy.id == policy_id).first()

    def get_by_id_for_customers(
        self, policy_id: int, customer_ids: Sequence[int]
    ) -> Optional[CompliancePolicy]:
        return self._customers_query(customer_ids).filter(CompliancePolicy.id == policy_id).first()

    def get_by_name_for_customer(self, name: str, customer_id: int) -> Optional[CompliancePolicy]:
        return self._customer_query(customer_id).filter(CompliancePolicy.name == name).first()

    def list_for_customer(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CompliancePolicy]:
        return self._customer_query(customer_id).offset(skip).limit(limit).all()

    def list_for_customers(
        self,
        customer_ids: Sequence[int],
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CompliancePolicy]:
        return self._customers_query(customer_ids).offset(skip).limit(limit).all()


class ComplianceResultRepository(SQLAlchemyRepository[ComplianceResult]):
    """Encapsulates all direct ComplianceResult ORM access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_customer(
        self,
        customer_id: int,
        *,
        policy_id: Optional[int] = None,
        device_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
    ) -> Sequence[ComplianceResult]:
        query = (
            self.session.query(ComplianceResult)
            .join(ComplianceResult.policy)
            .filter(CompliancePolicy.customer_id == customer_id)
        )

        if policy_id:
            query = query.filter(ComplianceResult.policy_id == policy_id)
        if device_id:
            query = query.filter(ComplianceResult.device_id == device_id)
        if status_filter:
            query = query.filter(ComplianceResult.status == status_filter)
        if start_ts:
            query = query.filter(ComplianceResult.ts >= start_ts)
        if end_ts:
            query = query.filter(ComplianceResult.ts <= end_ts)

        return query.order_by(ComplianceResult.ts.desc()).offset(skip).limit(limit).all()

    def list_for_customers(
        self,
        customer_ids: Sequence[int],
        *,
        policy_id: Optional[int] = None,
        device_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
    ) -> Sequence[ComplianceResult]:
        """List compliance results for multiple customers."""
        query = (
            self.session.query(ComplianceResult)
            .join(ComplianceResult.policy)
            .filter(CompliancePolicy.customer_id.in_(customer_ids))
        )

        if policy_id:
            query = query.filter(ComplianceResult.policy_id == policy_id)
        if device_id:
            query = query.filter(ComplianceResult.device_id == device_id)
        if status_filter:
            query = query.filter(ComplianceResult.status == status_filter)
        if start_ts:
            query = query.filter(ComplianceResult.ts >= start_ts)
        if end_ts:
            query = query.filter(ComplianceResult.ts <= end_ts)

        return query.order_by(ComplianceResult.ts.desc()).offset(skip).limit(limit).all()

    def get_by_id_for_customers(
        self, result_id: int, customer_ids: Sequence[int]
    ) -> Optional[ComplianceResult]:
        """Get a specific result ensuring access to any of the specified customers."""
        return (
            self.session.query(ComplianceResult)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(
                ComplianceResult.id == result_id,
                CompliancePolicy.customer_id.in_(customer_ids),
            )
            .first()
        )

    def get_device_with_customers_check(
        self, device_id: int, customer_ids: Sequence[int]
    ) -> Optional[Device]:
        """Get device by ID, filtered by multiple customers."""
        return (
            self.session.query(Device)
            .filter(
                Device.id == device_id,
                Device.customer_id.in_(customer_ids),
            )
            .first()
        )

    def get_latest_results_for_device_multi(
        self,
        device_id: int,
        customer_ids: Sequence[int],
    ) -> Sequence[ComplianceResult]:
        """Get the latest result for each policy for a device across multiple customers."""
        subquery = (
            self.session.query(
                ComplianceResult.policy_id,
                func.max(ComplianceResult.ts).label("max_ts"),
            )
            .join(ComplianceResult.policy)
            .filter(
                ComplianceResult.device_id == device_id,
                CompliancePolicy.customer_id.in_(customer_ids),
            )
            .group_by(ComplianceResult.policy_id)
            .subquery()
        )

        return (
            self.session.query(ComplianceResult)
            .join(
                subquery,
                (ComplianceResult.policy_id == subquery.c.policy_id)
                & (ComplianceResult.ts == subquery.c.max_ts),
            )
            .filter(ComplianceResult.device_id == device_id)
            .all()
        )

    def policy_stats_for_customers(self, customer_ids: Sequence[int]) -> list[dict]:
        """Aggregate pass/fail/error counts per policy for multiple customers."""
        status_case = {
            "pass": case((ComplianceResult.status == "pass", 1), else_=0),
            "fail": case((ComplianceResult.status == "fail", 1), else_=0),
            "error": case((ComplianceResult.status == "error", 1), else_=0),
        }
        rows = (
            self.session.query(
                ComplianceResult.policy_id,
                func.count(ComplianceResult.id).label("total"),
                func.sum(status_case["pass"]).label("pass_count"),
                func.sum(status_case["fail"]).label("fail_count"),
                func.sum(status_case["error"]).label("error_count"),
                func.max(ComplianceResult.ts).label("last_run"),
            )
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id.in_(customer_ids))
            .group_by(ComplianceResult.policy_id)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_recent_with_meta_multi(
        self, customer_ids: Sequence[int], limit: int = 20
    ) -> list[dict]:
        """List recent results including device hostname and policy name across customers."""
        rows = (
            self.session.query(
                ComplianceResult,
                Device.hostname.label("device_hostname"),
                CompliancePolicy.name.label("policy_name"),
            )
            .join(Device, Device.id == ComplianceResult.device_id)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id.in_(customer_ids))
            .order_by(ComplianceResult.ts.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": res.ComplianceResult.id,
                "policy_id": res.ComplianceResult.policy_id,
                "policy_name": res.policy_name,
                "device_id": res.ComplianceResult.device_id,
                "device_hostname": res.device_hostname,
                "job_id": res.ComplianceResult.job_id,
                "ts": res.ComplianceResult.ts,
                "status": res.ComplianceResult.status,
                "details_json": res.ComplianceResult.details_json,
            }
            for res in rows
        ]

    def latest_by_policy_multi(
        self, customer_ids: Sequence[int], per_policy_limit: int = 5
    ) -> list[dict]:
        """Latest results per device for each policy across customers (capped per policy)."""
        subquery = (
            self.session.query(
                ComplianceResult.policy_id,
                ComplianceResult.device_id,
                func.max(ComplianceResult.ts).label("max_ts"),
            )
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id.in_(customer_ids))
            .group_by(ComplianceResult.policy_id, ComplianceResult.device_id)
            .subquery()
        )

        rows = (
            self.session.query(
                ComplianceResult,
                Device.hostname.label("device_hostname"),
                CompliancePolicy.name.label("policy_name"),
            )
            .join(
                subquery,
                (ComplianceResult.policy_id == subquery.c.policy_id)
                & (ComplianceResult.device_id == subquery.c.device_id)
                & (ComplianceResult.ts == subquery.c.max_ts),
            )
            .join(Device, Device.id == ComplianceResult.device_id)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .order_by(ComplianceResult.policy_id.asc(), ComplianceResult.ts.desc())
            .all()
        )

        grouped: dict[int, list[dict]] = {}
        for res in rows:
            entry = {
                "id": res.ComplianceResult.id,
                "policy_id": res.ComplianceResult.policy_id,
                "policy_name": res.policy_name,
                "device_id": res.ComplianceResult.device_id,
                "device_hostname": res.device_hostname,
                "job_id": res.ComplianceResult.job_id,
                "ts": res.ComplianceResult.ts,
                "status": res.ComplianceResult.status,
                "details_json": res.ComplianceResult.details_json,
            }
            grouped.setdefault(res.ComplianceResult.policy_id, []).append(entry)

        trimmed: list[dict] = []
        for entries in grouped.values():
            trimmed.extend(entries[:per_policy_limit])
        return trimmed

    def get_latest_results_for_device(
        self,
        device_id: int,
        customer_id: int,
    ) -> Sequence[ComplianceResult]:
        """Get the latest result for each policy for a given device."""
        subquery = (
            self.session.query(
                ComplianceResult.policy_id,
                func.max(ComplianceResult.ts).label("max_ts"),
            )
            .join(ComplianceResult.policy)
            .filter(
                ComplianceResult.device_id == device_id,
                CompliancePolicy.customer_id == customer_id,
            )
            .group_by(ComplianceResult.policy_id)
            .subquery()
        )

        return (
            self.session.query(ComplianceResult)
            .join(
                subquery,
                (ComplianceResult.policy_id == subquery.c.policy_id)
                & (ComplianceResult.ts == subquery.c.max_ts),
            )
            .filter(ComplianceResult.device_id == device_id)
            .all()
        )

    def get_device_with_customer_check(self, device_id: int, customer_id: int) -> Optional[Device]:
        """Get device by ID, filtered by customer."""
        return (
            self.session.query(Device)
            .filter(
                Device.id == device_id,
                Device.customer_id == customer_id,
            )
            .first()
        )

    def get_by_id_for_customer(
        self, result_id: int, customer_id: int
    ) -> Optional[ComplianceResult]:
        """Get a specific result ensuring tenant isolation."""
        return (
            self.session.query(ComplianceResult)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(
                ComplianceResult.id == result_id,
                CompliancePolicy.customer_id == customer_id,
            )
            .first()
        )

    def policy_stats_for_customer(self, customer_id: int) -> list[dict]:
        """Aggregate pass/fail/error counts per policy for a customer."""
        status_case = {
            "pass": case((ComplianceResult.status == "pass", 1), else_=0),
            "fail": case((ComplianceResult.status == "fail", 1), else_=0),
            "error": case((ComplianceResult.status == "error", 1), else_=0),
        }
        rows = (
            self.session.query(
                ComplianceResult.policy_id,
                func.count(ComplianceResult.id).label("total"),
                func.sum(status_case["pass"]).label("pass_count"),
                func.sum(status_case["fail"]).label("fail_count"),
                func.sum(status_case["error"]).label("error_count"),
                func.max(ComplianceResult.ts).label("last_run"),
            )
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id == customer_id)
            .group_by(ComplianceResult.policy_id)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_recent_with_meta(self, customer_id: int, limit: int = 20) -> list[dict]:
        """List recent results including device hostname and policy name."""
        rows = (
            self.session.query(
                ComplianceResult,
                Device.hostname.label("device_hostname"),
                CompliancePolicy.name.label("policy_name"),
            )
            .join(Device, Device.id == ComplianceResult.device_id)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id == customer_id)
            .order_by(ComplianceResult.ts.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": res.ComplianceResult.id,
                "policy_id": res.ComplianceResult.policy_id,
                "policy_name": res.policy_name,
                "device_id": res.ComplianceResult.device_id,
                "device_hostname": res.device_hostname,
                "job_id": res.ComplianceResult.job_id,
                "ts": res.ComplianceResult.ts,
                "status": res.ComplianceResult.status,
                "details_json": res.ComplianceResult.details_json,
            }
            for res in rows
        ]

    def latest_by_policy(self, customer_id: int, per_policy_limit: int = 5) -> list[dict]:
        """Latest results per device for each policy (capped per policy)."""
        subquery = (
            self.session.query(
                ComplianceResult.policy_id,
                ComplianceResult.device_id,
                func.max(ComplianceResult.ts).label("max_ts"),
            )
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .filter(CompliancePolicy.customer_id == customer_id)
            .group_by(ComplianceResult.policy_id, ComplianceResult.device_id)
            .subquery()
        )

        rows = (
            self.session.query(
                ComplianceResult,
                Device.hostname.label("device_hostname"),
                CompliancePolicy.name.label("policy_name"),
            )
            .join(
                subquery,
                (ComplianceResult.policy_id == subquery.c.policy_id)
                & (ComplianceResult.device_id == subquery.c.device_id)
                & (ComplianceResult.ts == subquery.c.max_ts),
            )
            .join(Device, Device.id == ComplianceResult.device_id)
            .join(CompliancePolicy, CompliancePolicy.id == ComplianceResult.policy_id)
            .order_by(ComplianceResult.policy_id.asc(), ComplianceResult.ts.desc())
            .all()
        )

        grouped: dict[int, list[dict]] = {}
        for res in rows:
            entry = {
                "id": res.ComplianceResult.id,
                "policy_id": res.ComplianceResult.policy_id,
                "policy_name": res.policy_name,
                "device_id": res.ComplianceResult.device_id,
                "device_hostname": res.device_hostname,
                "job_id": res.ComplianceResult.job_id,
                "ts": res.ComplianceResult.ts,
                "status": res.ComplianceResult.status,
                "details_json": res.ComplianceResult.details_json,
            }
            grouped.setdefault(res.ComplianceResult.policy_id, []).append(entry)

        trimmed: list[dict] = []
        for entries in grouped.values():
            trimmed.extend(entries[:per_policy_limit])
        return trimmed

"""Compliance persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func
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

    def get_by_id(self, policy_id: int) -> Optional[CompliancePolicy]:
        return self.session.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()

    def get_by_id_for_customer(
        self, policy_id: int, customer_id: int
    ) -> Optional[CompliancePolicy]:
        return self._customer_query(customer_id).filter(CompliancePolicy.id == policy_id).first()

    def get_by_name_for_customer(self, name: str, customer_id: int) -> Optional[CompliancePolicy]:
        return self._customer_query(customer_id).filter(CompliancePolicy.name == name).first()

    def list_for_customer(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CompliancePolicy]:
        return self._customer_query(customer_id).offset(skip).limit(limit).all()


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

        return query.order_by(ComplianceResult.ts.desc()).offset(skip).limit(limit).all()

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

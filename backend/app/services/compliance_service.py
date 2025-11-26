"""Compliance management service layer."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import CompliancePolicy, ComplianceResult, User
from app.domain.context import TenantRequestContext
from app.domain.exceptions import ConflictError, NotFoundError
from app.repositories import CompliancePolicyRepository, ComplianceResultRepository


class ComplianceService:
    """Business logic for compliance policy and result operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.policies = CompliancePolicyRepository(session)
        self.results = ComplianceResultRepository(session)

    # -------------------------------------------------------------------------
    # Policy Operations

    def list_policies(
        self,
        context: TenantRequestContext,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CompliancePolicy]:
        """List compliance policies for the active customer."""
        return self.policies.list_for_customer(context.customer_id, skip=skip, limit=limit)

    def get_policy(
        self,
        policy_id: int,
        context: TenantRequestContext,
    ) -> CompliancePolicy:
        """Get a compliance policy by ID."""
        policy = self.policies.get_by_id_for_customer(policy_id, context.customer_id)
        if not policy:
            raise NotFoundError("Policy not found")
        return policy

    def create_policy(
        self,
        name: str,
        definition_yaml: str,
        scope_json: dict,
        user: User,
        context: TenantRequestContext,
        description: Optional[str] = None,
    ) -> CompliancePolicy:
        """Create a new compliance policy."""
        existing = self.policies.get_by_name_for_customer(name, context.customer_id)
        if existing:
            raise ConflictError("Policy with this name already exists for this customer")

        policy = CompliancePolicy(
            name=name,
            description=description,
            scope_json=scope_json,
            definition_yaml=definition_yaml,
            created_by=user.id,
            customer_id=context.customer_id,
        )
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    # -------------------------------------------------------------------------
    # Result Operations

    def list_results(
        self,
        context: TenantRequestContext,
        *,
        policy_id: Optional[int] = None,
        device_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ComplianceResult]:
        """List compliance results with optional filters."""
        return self.results.list_for_customer(
            context.customer_id,
            policy_id=policy_id,
            device_id=device_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit,
        )

    def get_device_compliance_summary(
        self,
        device_id: int,
        context: TenantRequestContext,
    ) -> dict:
        """Get compliance summary for a device across all policies."""
        # Verify device tenancy
        device = self.results.get_device_with_customer_check(device_id, context.customer_id)
        if not device:
            raise NotFoundError("Device not found")

        # Get latest result for each policy
        results = self.results.get_latest_results_for_device(device_id, context.customer_id)

        summary = {"device_id": device_id, "policies": []}

        for result in results:
            policy = self.policies.get_by_id(result.policy_id)
            summary["policies"].append(
                {
                    "policy_id": result.policy_id,
                    "policy_name": policy.name if policy else "Unknown",
                    "status": result.status,
                    "last_check": result.ts,
                    "details": result.details_json,
                }
            )

        return summary

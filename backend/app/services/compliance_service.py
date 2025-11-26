"""Compliance management service layer."""

from __future__ import annotations

from datetime import datetime
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

    def update_policy(
        self,
        policy_id: int,
        context: TenantRequestContext,
        name: Optional[str] = None,
        definition_yaml: Optional[str] = None,
        scope_json: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> CompliancePolicy:
        """Update an existing compliance policy."""
        policy = self.get_policy(policy_id, context)

        if name is not None and name != policy.name:
            existing = self.policies.get_by_name_for_customer(name, context.customer_id)
            if existing:
                raise ConflictError("Policy with this name already exists for this customer")
            policy.name = name

        if definition_yaml is not None:
            policy.definition_yaml = definition_yaml

        if scope_json is not None:
            policy.scope_json = scope_json

        if description is not None:
            policy.description = description

        self.session.commit()
        self.session.refresh(policy)
        return policy

    def delete_policy(
        self,
        policy_id: int,
        context: TenantRequestContext,
    ) -> None:
        """Delete a compliance policy."""
        policy = self.get_policy(policy_id, context)
        self.session.delete(policy)
        self.session.commit()

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
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
    ) -> Sequence[ComplianceResult]:
        """List compliance results with optional filters."""
        return self.results.list_for_customer(
            context.customer_id,
            policy_id=policy_id,
            device_id=device_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit,
            start_ts=start_ts,
            end_ts=end_ts,
        )

    def get_overview(self, context: TenantRequestContext, recent_limit: int = 20) -> dict:
        """Provide per-policy stats and recent results for dashboards."""
        policies = self.policies.list_for_customer(context.customer_id)
        stats_rows = self.results.policy_stats_for_customer(context.customer_id)
        stats_map = {row["policy_id"]: row for row in stats_rows}

        policy_stats: list[dict] = []
        for policy in policies:
            stat = stats_map.get(policy.id, {})
            policy_stats.append(
                {
                    "policy_id": policy.id,
                    "name": policy.name,
                    "description": policy.description,
                    "total": int(stat.get("total", 0) or 0),
                    "pass_count": int(stat.get("pass_count", 0) or 0),
                    "fail_count": int(stat.get("fail_count", 0) or 0),
                    "error_count": int(stat.get("error_count", 0) or 0),
                    "last_run": stat.get("last_run"),
                }
            )

        recent = self.results.list_recent_with_meta(context.customer_id, limit=recent_limit)
        latest_by_policy = self.results.latest_by_policy(context.customer_id)
        return {
            "policies": policy_stats,
            "recent_results": recent,
            "latest_by_policy": latest_by_policy,
        }

    def get_result(self, result_id: int, context: TenantRequestContext) -> ComplianceResult:
        """Fetch a specific compliance result scoped to the active customer."""
        result = self.results.get_by_id_for_customer(result_id, context.customer_id)
        if not result:
            raise NotFoundError("Result not found")
        return result

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

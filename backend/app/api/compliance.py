"""Compliance API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.celery_app import celery_app
from app.core.auth import require_admin
from app.db import User
from app.dependencies import (
    get_compliance_service,
    get_job_service,
    get_multi_tenant_context,
    get_operator_context,
)
from app.domain.context import MultiTenantContext, TenantRequestContext
from app.schemas.compliance import (
    ComplianceOverviewResponse,
    ComplianceResultResponse,
    DeviceComplianceSummary,
    PolicyCreate,
    PolicyListResponse,
    PolicyResponse,
    PolicyStatsResponse,
    PolicyUpdate,
    RunComplianceRequest,
)
from app.services.compliance_service import ComplianceService
from app.services.job_service import JobService

router = APIRouter(prefix="/compliance", tags=["compliance"])


# Policy endpoints
@router.get("/policies", response_model=list[PolicyListResponse])
def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> list[PolicyListResponse]:
    """List compliance policies for accessible customers."""
    policies = service.list_policies_multi_tenant(context, skip=skip, limit=limit)
    return [PolicyListResponse.model_validate(p) for p in policies]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> PolicyResponse:
    """Get compliance policy."""
    policy = service.get_policy_multi_tenant(policy_id, context)
    return PolicyResponse.model_validate(policy)


@router.post("/policies", status_code=status.HTTP_201_CREATED, response_model=PolicyResponse)
def create_policy(
    payload: PolicyCreate,
    service: ComplianceService = Depends(get_compliance_service),
    current_user: User = Depends(require_admin),
    context: TenantRequestContext = Depends(get_operator_context),
) -> PolicyResponse:
    """Create compliance policy (admin only)."""
    policy = service.create_policy(
        name=payload.name,
        definition_yaml=payload.definition_yaml,
        scope_json=payload.scope_json,
        user=current_user,
        context=context,
        description=payload.description,
    )
    return PolicyResponse.model_validate(policy)


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    service: ComplianceService = Depends(get_compliance_service),
    current_user: User = Depends(require_admin),
    context: TenantRequestContext = Depends(get_operator_context),
) -> PolicyResponse:
    """Update compliance policy (admin only)."""
    policy = service.update_policy(
        policy_id=policy_id,
        context=context,
        name=payload.name,
        definition_yaml=payload.definition_yaml,
        scope_json=payload.scope_json,
        description=payload.description,
    )
    return PolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    current_user: User = Depends(require_admin),
    context: TenantRequestContext = Depends(get_operator_context),
) -> None:
    """Delete compliance policy (admin only)."""
    service.delete_policy(policy_id, context)


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_compliance_check(
    request: RunComplianceRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
    job_service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Run compliance check for a policy."""
    # Verify policy exists and user has access
    policy = compliance_service.get_policy(request.policy_id, context)

    job = job_service.create_job(
        job_type="compliance_check",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={"policy_id": policy.id, "policy_name": policy.name},
        payload={"policy_id": policy.id},
    )

    celery_app.send_task(
        "compliance_check_job",
        args=[job.id, policy.id],
    )

    return {"job_id": job.id, "status": "queued"}


# Results endpoints
@router.get("/results", response_model=list[ComplianceResultResponse])
def list_compliance_results(
    policy_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> list[ComplianceResultResponse]:
    """List compliance results with filters."""
    results = service.list_results_multi_tenant(
        context,
        policy_id=policy_id,
        device_id=device_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
        start_ts=start,
        end_ts=end,
    )
    return [ComplianceResultResponse.model_validate(r) for r in results]


@router.get("/overview", response_model=ComplianceOverviewResponse)
def compliance_overview(
    recent_limit: int = Query(20, ge=1, le=200),
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> ComplianceOverviewResponse:
    """Return aggregated compliance stats and recent results for dashboards."""
    overview = service.get_overview_multi_tenant(context, recent_limit=recent_limit)
    return ComplianceOverviewResponse(
        policies=[PolicyStatsResponse.model_validate(p) for p in overview["policies"]],
        recent_results=[
            ComplianceResultResponse.model_validate(r) for r in overview["recent_results"]
        ],
        latest_by_policy=[
            ComplianceResultResponse.model_validate(r) for r in overview["latest_by_policy"]
        ],
    )


@router.get("/results/{result_id}", response_model=ComplianceResultResponse)
def get_compliance_result(
    result_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> ComplianceResultResponse:
    """Get a specific compliance result (scoped to accessible customers)."""
    result = service.get_result_multi_tenant(result_id, context)
    return ComplianceResultResponse.model_validate(result)


@router.get("/devices/{device_id}", response_model=DeviceComplianceSummary)
def get_device_compliance(
    device_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> DeviceComplianceSummary:
    """Get compliance summary for a device across all policies."""
    summary = service.get_device_compliance_summary_multi_tenant(device_id, context)
    return DeviceComplianceSummary(**summary)

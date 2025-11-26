"""Compliance API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.celery_app import celery_app
from app.core.auth import require_admin
from app.db import User
from app.dependencies import (
    get_compliance_service,
    get_job_service,
    get_operator_context,
    get_tenant_context,
)
from app.domain.context import TenantRequestContext
from app.schemas.compliance import (
    ComplianceResultResponse,
    DeviceComplianceSummary,
    PolicyCreate,
    PolicyListResponse,
    PolicyResponse,
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
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[PolicyListResponse]:
    """List compliance policies for the active customer."""
    policies = service.list_policies(context, skip=skip, limit=limit)
    return [PolicyListResponse.model_validate(p) for p in policies]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> PolicyResponse:
    """Get compliance policy."""
    policy = service.get_policy(policy_id, context)
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
    service: ComplianceService = Depends(get_compliance_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[ComplianceResultResponse]:
    """List compliance results with filters."""
    results = service.list_results(
        context,
        policy_id=policy_id,
        device_id=device_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    return [ComplianceResultResponse.model_validate(r) for r in results]


@router.get("/devices/{device_id}", response_model=DeviceComplianceSummary)
def get_device_compliance(
    device_id: int,
    service: ComplianceService = Depends(get_compliance_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> DeviceComplianceSummary:
    """Get compliance summary for a device across all policies."""
    summary = service.get_device_compliance_summary(device_id, context)
    return DeviceComplianceSummary(**summary)

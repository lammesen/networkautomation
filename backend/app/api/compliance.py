"""Compliance API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import errors
from app.core.auth import (
    get_current_active_customer,
    get_current_user,
    require_admin,
    require_operator,
)
from app.db import CompliancePolicy, ComplianceResult, Customer, Device, User, get_db
from app.dependencies import get_job_service, get_operator_context
from app.domain.context import TenantRequestContext
from app.domain.exceptions import DomainError
from app.services.job_service import JobService
from app.celery_app import celery_app

router = APIRouter(prefix="/compliance", tags=["compliance"])


# Policy endpoints
@router.get("/policies")
def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_customer: Customer = Depends(get_current_active_customer),
) -> list[dict]:
    """List compliance policies for the active customer."""
    policies = (
        db.query(CompliancePolicy)
        .filter(CompliancePolicy.customer_id == active_customer.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "scope_json": p.scope_json,
            "created_by": p.created_by,
            "created_at": p.created_at,
        }
        for p in policies
    ]


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_customer: Customer = Depends(get_current_active_customer),
) -> dict:
    """Get compliance policy."""
    policy = (
        db.query(CompliancePolicy)
        .filter(
            CompliancePolicy.id == policy_id,
            CompliancePolicy.customer_id == active_customer.id,
        )
        .first()
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    
    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "scope_json": policy.scope_json,
        "definition_yaml": policy.definition_yaml,
        "created_by": policy.created_by,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(
    name: str,
    definition_yaml: str,
    scope_json: dict,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    active_customer: Customer = Depends(get_current_active_customer),
) -> dict:
    """Create compliance policy (admin only)."""
    existing = (
        db.query(CompliancePolicy)
        .filter(
            CompliancePolicy.name == name,
            CompliancePolicy.customer_id == active_customer.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy with this name already exists for this customer",
        )
    
    policy = CompliancePolicy(
        name=name,
        description=description,
        scope_json=scope_json,
        definition_yaml=definition_yaml,
        created_by=current_user.id,
        customer_id=active_customer.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "scope_json": policy.scope_json,
        "created_at": policy.created_at,
    }


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_compliance_check(
    policy_id: int,
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Run compliance check for a policy."""
    policy = (
        db.query(CompliancePolicy)
        .filter(
            CompliancePolicy.id == policy_id,
            CompliancePolicy.customer_id == context.customer_id,
        )
        .first()
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    
    try:
        job = service.create_job(
            job_type="compliance_check",
            user=context.user,
            customer_id=context.customer_id,
            target_summary={"policy_id": policy_id, "policy_name": policy.name},
            payload={"policy_id": policy_id},
        )
    except DomainError as exc:
        raise errors.to_http(exc)

    celery_app.send_task(
        "compliance_check_job",
        args=[job.id, policy_id],
    )
    
    return {"job_id": job.id, "status": "queued"}


# Results endpoints
@router.get("/results")
def list_compliance_results(
    policy_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_customer: Customer = Depends(get_current_active_customer),
) -> list[dict]:
    """List compliance results with filters."""
    query = (
        db.query(ComplianceResult)
        .join(ComplianceResult.policy)
        .filter(CompliancePolicy.customer_id == active_customer.id)
    )
    
    if policy_id:
        query = query.filter(ComplianceResult.policy_id == policy_id)
    
    if device_id:
        query = query.filter(ComplianceResult.device_id == device_id)
    
    if status_filter:
        query = query.filter(ComplianceResult.status == status_filter)
    
    results = query.order_by(ComplianceResult.ts.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "policy_id": r.policy_id,
            "device_id": r.device_id,
            "job_id": r.job_id,
            "ts": r.ts,
            "status": r.status,
            "details_json": r.details_json,
        }
        for r in results
    ]


@router.get("/devices/{device_id}")
def get_device_compliance(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_customer: Customer = Depends(get_current_active_customer),
) -> dict:
    """Get compliance summary for a device across all policies."""
    # Verify device tenancy
    device = (
        db.query(Device)
        .filter(
            Device.id == device_id,
            Device.customer_id == active_customer.id,
        )
        .first()
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Get latest result for each policy (filtered by customer policies)
    from sqlalchemy import func
    
    subquery = (
        db.query(
            ComplianceResult.policy_id,
            func.max(ComplianceResult.ts).label("max_ts"),
        )
        .join(ComplianceResult.policy)
        .filter(
            ComplianceResult.device_id == device_id,
            CompliancePolicy.customer_id == active_customer.id,
        )
        .group_by(ComplianceResult.policy_id)
        .subquery()
    )
    
    results = (
        db.query(ComplianceResult)
        .join(
            subquery,
            (ComplianceResult.policy_id == subquery.c.policy_id)
            & (ComplianceResult.ts == subquery.c.max_ts),
        )
        .filter(ComplianceResult.device_id == device_id)
        .all()
    )
    
    summary = {"device_id": device_id, "policies": []}
    
    for result in results:
        policy = db.query(CompliancePolicy).filter(CompliancePolicy.id == result.policy_id).first()
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

from __future__ import annotations

import json
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.compliance.models import CompliancePolicy, ComplianceResult
from app.core.deps import get_current_user, role_required
from app.db.session import get_db

router = APIRouter(prefix="/compliance", tags=["compliance"], dependencies=[Depends(get_current_user)])


class CompliancePolicyCreate(BaseModel):
    name: str
    scope: Optional[dict] = None
    definition: dict


class CompliancePolicyUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[dict] = None
    definition: Optional[dict] = None


@router.get("/policies")
def list_policies(db: Session = Depends(get_db)):
    policies = db.query(CompliancePolicy).order_by(CompliancePolicy.name).all()
    return [
        {
            "id": policy.id,
            "name": policy.name,
            "scope": json.loads(policy.scope_json or "{}"),
            "definition": yaml.safe_load(policy.definition_yaml) if policy.definition_yaml else {},
            "created_at": policy.created_at,
        }
        for policy in policies
    ]


@router.post("/policies", dependencies=[Depends(role_required("admin"))])
def create_policy(payload: CompliancePolicyCreate, db: Session = Depends(get_db)):
    policy = CompliancePolicy(
        name=payload.name,
        scope_json=json.dumps(payload.scope or {}),
        definition_yaml=yaml.safe_dump(payload.definition),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.put("/policies/{policy_id}", dependencies=[Depends(role_required("admin"))])
def update_policy(policy_id: int, payload: CompliancePolicyUpdate, db: Session = Depends(get_db)):
    policy = db.get(CompliancePolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404)
    if payload.name is not None:
        policy.name = payload.name
    if payload.scope is not None:
        policy.scope_json = json.dumps(payload.scope)
    if payload.definition is not None:
        policy.definition_yaml = yaml.safe_dump(payload.definition)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/policies/{policy_id}", status_code=204, dependencies=[Depends(role_required("admin"))])
def delete_policy(policy_id: int, db: Session = Depends(get_db)) -> None:
    policy = db.get(CompliancePolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404)
    db.delete(policy)
    db.commit()


@router.get("/results")
def list_results(
    db: Session = Depends(get_db),
    policy_id: Optional[int] = Query(default=None),
    device_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    query = db.query(ComplianceResult)
    if policy_id:
        query = query.filter(ComplianceResult.policy_id == policy_id)
    if device_id:
        query = query.filter(ComplianceResult.device_id == device_id)
    if status:
        query = query.filter(ComplianceResult.status == status)
    results = query.order_by(ComplianceResult.ts.desc()).all()
    return [
        {
            "id": result.id,
            "policy_id": result.policy_id,
            "device_id": result.device_id,
            "job_id": result.job_id,
            "ts": result.ts,
            "status": result.status,
            "details": json.loads(result.details_json or "{}"),
        }
        for result in results
    ]


@router.get("/devices/{device_id}")
def device_compliance_summary(device_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(ComplianceResult)
        .filter(ComplianceResult.device_id == device_id)
        .order_by(ComplianceResult.ts.desc())
        .all()
    )
    summary = {}
    for result in results:
        summary.setdefault(result.policy_id, result.status)
    return summary

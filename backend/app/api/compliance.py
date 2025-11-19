from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import compliance as crud_compliance
from app.db.session import get_db
from app.api.auth import require_role
from app.db.models import UserRole, JobType
from app.jobs.compliance import compliance_job
from app.crud.job import create_job

router = APIRouter()


@router.get("/policies", response_model=List[schemas.compliance.CompliancePolicy])
def read_policies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    return crud_compliance.get_policies(db, skip=skip, limit=limit)


@router.get("/policies/{policy_id}", response_model=schemas.compliance.CompliancePolicy)
def read_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    db_policy = crud_compliance.get_policy(db, policy_id=policy_id)
    if db_policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db_policy


@router.post("/policies", response_model=schemas.compliance.CompliancePolicy)
def create_policy(
    policy: schemas.compliance.CompliancePolicyCreate,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.admin)),
):
    return crud_compliance.create_policy(db=db, policy=policy, user=current_user)


@router.delete("/policies/{policy_id}", response_model=schemas.compliance.CompliancePolicy)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.admin)),
):
    db_policy = crud_compliance.get_policy(db, policy_id=policy_id)
    if not db_policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return crud_compliance.delete_policy(db=db, db_policy=db_policy)


@router.post("/run", response_model=schemas.job.Job)
def run_compliance(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    policy = crud_compliance.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    job = create_job(
        db,
        schemas.job.JobCreate(
            type=JobType.compliance_run,
            target_summary_json={"policy_id": policy_id},
        ),
        current_user,
    )
    compliance_job.delay(job_id=job.id, policy_id=policy_id)
    return job


@router.get("/results", response_model=List[schemas.compliance.ComplianceResult])
def get_results(
    policy_id: Optional[int] = None,
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    return crud_compliance.get_compliance_results(db, policy_id=policy_id, device_id=device_id, status=status)

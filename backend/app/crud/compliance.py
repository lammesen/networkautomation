from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models import CompliancePolicy, ComplianceResult, User
from app.schemas.compliance import CompliancePolicyCreate


def get_policy(db: Session, policy_id: int) -> Optional[CompliancePolicy]:
    return db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()


def get_policies(db: Session, skip: int = 0, limit: int = 100) -> List[CompliancePolicy]:
    return db.query(CompliancePolicy).offset(skip).limit(limit).all()


def create_policy(db: Session, policy: CompliancePolicyCreate, user: User) -> CompliancePolicy:
    db_policy = CompliancePolicy(**policy.model_dump(), created_by_id=user.id)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


def delete_policy(db: Session, db_policy: CompliancePolicy):
    db.delete(db_policy)
    db.commit()
    return db_policy


def create_compliance_result(db: Session, policy_id: int, device_id: int, job_id: int, status: str, details: dict) -> ComplianceResult:
    result = ComplianceResult(
        policy_id=policy_id,
        device_id=device_id,
        job_id=job_id,
        status=status,
        details_json=details,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_compliance_results(db: Session, policy_id: Optional[int] = None, device_id: Optional[int] = None, status: Optional[str] = None) -> List[ComplianceResult]:
    query = db.query(ComplianceResult)
    if policy_id:
        query = query.filter(ComplianceResult.policy_id == policy_id)
    if device_id:
        query = query.filter(ComplianceResult.device_id == device_id)
    if status:
        query = query.filter(ComplianceResult.status == status)
    return query.all()

from __future__ import annotations

import json
from typing import Iterable, List

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.jobs.models import Job


def create_job(db: Session, job_type: str, user_id: int | None, targets: dict | None = None) -> Job:
    job = Job(
        type=job_type,
        status="pending",
        user_id=user_id,
        requested_at=utcnow(),
        target_summary_json=json.dumps(targets or {}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

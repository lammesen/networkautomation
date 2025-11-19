"""Command execution API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import require_operator
from app.db import get_db, User
from app.schemas.job import CommandRunRequest
from app.jobs.manager import create_job
from celery_app import celery_app

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_commands(
    request: CommandRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> dict:
    """Run commands on target devices."""
    # Create job
    job = create_job(
        db=db,
        job_type="run_commands",
        user=current_user,
        target_summary={"filters": request.targets},
        payload={
            "commands": request.commands,
            "timeout": request.timeout_sec,
        },
    )
    
    # Enqueue Celery task
    celery_app.send_task(
        "run_commands_job",
        args=[job.id, request.targets, request.commands, request.timeout_sec],
    )
    
    return {"job_id": job.id, "status": "queued"}

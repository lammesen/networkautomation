from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.crud import job as crud_job
from app.db.session import get_db
from app.api.auth import require_role
from app.db.models import UserRole, JobType
from app.jobs.run_commands import run_commands_job

router = APIRouter()


@router.post("/run", response_model=schemas.job.Job)
def run_commands(
    command_run: schemas.command.CommandRun,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    job = crud_job.create_job(
        db,
        schemas.job.JobCreate(
            type=JobType.run_commands,
            target_summary_json=command_run.targets,
        ),
        current_user,
    )
    run_commands_job.delay(
        job_id=job.id,
        targets=command_run.targets,
        commands=command_run.commands,
        timeout=command_run.timeout_sec,
    )
    return job

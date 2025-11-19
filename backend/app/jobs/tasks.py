import time
from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.crud.job import get_job, update_job_status, create_job_log_and_publish
from app.db.models import JobStatus
from app.automation.nornir_init import init_nornir


@shared_task(bind=True)
def run_job(self, job_id: int):
    """
    Generic job execution flow.
    """
    db: Session = SessionLocal()
    job = get_job(db, job_id)
    if not job:
        return

    update_job_status(db, job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} started.")

    try:
        # Simulate some work
        time.sleep(10)
        # Here we would call the appropriate automation task
        # e.g., run_commands_task(job_id, targets, commands)
        update_job_status(db, job, JobStatus.success)
        create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} completed successfully.")
    except Exception as e:
        update_job_status(db, job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()

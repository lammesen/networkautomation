from celery import shared_task
from sqlalchemy.orm import Session
from nornir.core.task import Result

from app.db.session import SessionLocal
from app.crud.job import get_job, update_job_status, create_job_log_and_publish
from app.db.models import JobStatus
from app.automation.nornir_init import init_nornir
from app.automation.tasks_cli import run_commands
from app.crud.device import get_devices


@shared_task(bind=True)
def run_commands_job(self, job_id: int, targets: dict, commands: list, timeout: int):
    db: Session = SessionLocal()
    job = get_job(db, job_id)
    if not job:
        return

    update_job_status(db, job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} started: Running commands.")

    try:
        devices = get_devices(db, **targets)
        if not devices:
            update_job_status(db, job, JobStatus.failed)
            create_job_log_and_publish(db, job_id, "ERROR", "No devices matched the provided targets.")
            return

        nr = init_nornir(db)
        # TODO: Filter the inventory to only the targeted devices

        results = nr.run(task=run_commands, commands=commands)

        failed_hosts = set()
        for host, result in results.items():
            if result.failed:
                failed_hosts.add(host)
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: {result.exception}", host=host)
            else:
                output = result[1].result
                create_job_log_and_publish(db, job_id, "INFO", f"Host {host}:\n{output}", host=host)

        if failed_hosts:
            status = JobStatus.partial_fail if len(failed_hosts) < len(nr.inventory.hosts) else JobStatus.failed
            update_job_status(db, job, status)
            create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} completed with failures on hosts: {', '.join(failed_hosts)}")
        else:
            update_job_status(db, job, JobStatus.success)
            create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} completed successfully.")

    except Exception as e:
        update_job_status(db, job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()

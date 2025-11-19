from celery import shared_task
from sqlalchemy.orm import Session
import hashlib

from app.db.session import SessionLocal
from app.crud.job import get_job, update_job_status, create_job_log_and_publish
from app.db.models import JobStatus, ConfigSnapshot
from app.automation.nornir_init import init_nornir
from app.automation.tasks_config import get_config
from app.crud.device import get_devices


def has_config_changed(db: Session, device_id: int, new_config: str) -> bool:
    last_snapshot = db.query(ConfigSnapshot).filter(ConfigSnapshot.device_id == device_id).order_by(ConfigSnapshot.created_at.desc()).first()
    if not last_snapshot:
        return True

    new_hash = hashlib.sha256(new_config.encode()).hexdigest()
    return new_hash != last_snapshot.hash


@shared_task(bind=True)
def config_backup_job(self, job_id: int, targets: dict, source_label: str):
    db: Session = SessionLocal()
    job = get_job(db, job_id)
    if not job:
        return

    update_job_status(db, job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} started: Configuration backup.")

    try:
        devices = get_devices(db, **targets)
        if not devices:
            update_job_status(db, job, JobStatus.failed)
            create_job_log_and_publish(db, job_id, "ERROR", "No devices matched the provided targets.")
            return

        nr = init_nornir(db)
        # TODO: Filter the inventory to only the targeted devices

        results = nr.run(task=get_config)

        failed_hosts = set()
        changed_hosts = set()
        for host, result in results.items():
            device = next((d for d in devices if d.hostname == host), None)
            if not device:
                continue

            if result.failed:
                failed_hosts.add(host)
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: {result.exception}", host=host)
            else:
                config_text = result.result
                if has_config_changed(db, device.id, config_text):
                    changed_hosts.add(host)
                    snapshot = ConfigSnapshot(
                        device_id=device.id,
                        job_id=job_id,
                        source=source_label,
                        config_text=config_text,
                        hash=hashlib.sha256(config_text.encode()).hexdigest(),
                    )
                    db.add(snapshot)
                    db.commit()
                    create_job_log_and_publish(db, job_id, "INFO", f"Host {host}: Configuration changed and backed up.", host=host)
                else:
                    create_job_log_and_publish(db, job_id, "INFO", f"Host {host}: No configuration change.", host=host)

        if failed_hosts:
            status = JobStatus.partial_fail if len(failed_hosts) < len(nr.inventory.hosts) else JobStatus.failed
            update_job_status(db, job, status)
            create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} completed with failures on hosts: {', '.join(failed_hosts)}")
        else:
            update_job_status(db, job, JobStatus.success)
            create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} completed successfully. Changes detected on: {', '.join(changed_hosts) or 'None'}")

    except Exception as e:
        update_job_status(db, job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()

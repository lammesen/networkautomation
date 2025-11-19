from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.crud.job import get_job, update_job_status, create_job_log_and_publish
from app.crud.compliance import get_policy, create_compliance_result
from app.db.models import JobStatus, ComplianceStatus
from app.automation.nornir_init import init_nornir
from app.automation.tasks_validate import run_validation
from app.crud.device import get_devices


@shared_task(bind=True)
def compliance_job(self, job_id: int, policy_id: int):
    db: Session = SessionLocal()
    job = get_job(db, job_id)
    policy = get_policy(db, policy_id)
    if not job or not policy:
        return

    update_job_status(db, job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} started: Compliance run for policy '{policy.name}'.")

    try:
        targets = policy.scope_json
        devices = get_devices(db, **targets)
        if not devices:
            update_job_status(db, job, JobStatus.failed)
            create_job_log_and_publish(db, job_id, "ERROR", "No devices matched the policy scope.")
            return

        nr = init_nornir(db)
        # TODO: Filter inventory

        results = nr.run(task=run_validation, validation_source=policy.definition_yaml)

        failed_hosts = set()
        non_compliant_hosts = set()

        for host, result in results.items():
            device = next((d for d in devices if d.hostname == host), None)
            if not device:
                continue

            if result.failed:
                failed_hosts.add(host)
                create_compliance_result(db, policy_id, device.id, job_id, ComplianceStatus.error, {"error": str(result.exception)})
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: Validation failed: {result.exception}", host=host)
            else:
                validation_result = result.result
                if validation_result['complies']:
                    status = ComplianceStatus.compliant
                else:
                    status = ComplianceStatus.non_compliant
                    non_compliant_hosts.add(host)

                create_compliance_result(db, policy_id, device.id, job_id, status, validation_result)
                create_job_log_and_publish(db, job_id, "INFO", f"Host {host}: Compliance status: {status.value}", host=host)

        if failed_hosts or non_compliant_hosts:
            status = JobStatus.partial_fail
        else:
            status = JobStatus.success

        update_job_status(db, job, status)
        create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} completed.")

    except Exception as e:
        update_job_status(db, job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()

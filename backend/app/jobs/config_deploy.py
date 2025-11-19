from celery import shared_task
from sqlalchemy.orm import Session
import json

from app.db.session import SessionLocal
from app.crud.job import get_job, update_job_status, create_job_log_and_publish
from app.db.models import JobStatus
from app.automation.nornir_init import init_nornir
from app.automation.tasks_config import load_merge_candidate, compare_config, commit_config, rollback_config
from app.crud.device import get_devices


@shared_task(bind=True)
def config_deploy_preview_job(self, job_id: int, targets: dict, snippet: str):
    db: Session = SessionLocal()
    job = get_job(db, job_id)
    if not job:
        return

    update_job_status(db, job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", f"Job {job_id} started: Configuration deployment preview.")

    try:
        devices = get_devices(db, **targets)
        if not devices:
            update_job_status(db, job, JobStatus.failed)
            create_job_log_and_publish(db, job_id, "ERROR", "No devices matched the provided targets.")
            return

        nr = init_nornir(db)
        # TODO: Filter inventory

        # Load candidate config
        load_results = nr.run(task=load_merge_candidate, config=snippet)

        diff_results = {}
        failed_hosts = set()

        for host, result in load_results.items():
            if result.failed:
                failed_hosts.add(host)
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: Failed to load candidate config: {result.exception}", host=host)
                continue

            # Compare config
            compare_result = nr.run(task=compare_config, on_hosts=[host])
            if compare_result[host].failed:
                failed_hosts.add(host)
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: Failed to compare config: {compare_result[host].exception}", host=host)
            else:
                diff = compare_result[host].result
                diff_results[host] = diff
                create_job_log_and_publish(db, job_id, "INFO", f"Host {host}:\n{diff}", host=host)

        job.result_summary_json = {"diffs": diff_results, "failed_hosts": list(failed_hosts), "snippet": snippet}
        db.commit()

        if failed_hosts:
            status = JobStatus.partial_fail if len(failed_hosts) < len(nr.inventory.hosts) else JobStatus.failed
            update_job_status(db, job, status)
        else:
            update_job_status(db, job, JobStatus.success)

    except Exception as e:
        update_job_status(db, job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()


@shared_task(bind=True)
def config_deploy_commit_job(self, job_id: int, preview_job_id: int):
    db: Session = SessionLocal()
    commit_job = get_job(db, job_id)
    preview_job = get_job(db, preview_job_id)

    if not commit_job or not preview_job:
        # Log error and exit
        return

    update_job_status(db, commit_job, JobStatus.running)
    create_job_log_and_publish(db, job_id, "INFO", "Starting configuration commit.")

    try:
        targets = preview_job.target_summary_json
        snippet = preview_job.result_summary_json.get("snippet")

        if not snippet:
            update_job_status(db, commit_job, JobStatus.failed)
            create_job_log_and_publish(db, job_id, "ERROR", "Could not find snippet from preview job.")
            return

        nr = init_nornir(db)
        # TODO: Filter inventory

        load_results = nr.run(task=load_merge_candidate, config=snippet)
        commit_results = {}
        failed_hosts = set()

        for host, result in load_results.items():
            if result.failed:
                failed_hosts.add(host)
                continue

            commit_result = nr.run(task=commit_config, on_hosts=[host])
            if commit_result[host].failed:
                failed_hosts.add(host)
                create_job_log_and_publish(db, job_id, "ERROR", f"Host {host}: Commit failed. Attempting rollback.", host=host)
                nr.run(task=rollback_config, on_hosts=[host])
            else:
                commit_results[host] = "Success"
                create_job_log_and_publish(db, job_id, "INFO", f"Host {host}: Commit successful.", host=host)

        if failed_hosts:
            update_job_status(db, commit_job, JobStatus.partial_fail)
        else:
            update_job_status(db, commit_job, JobStatus.success)

    except Exception as e:
        update_job_status(db, commit_job, JobStatus.failed)
        create_job_log_and_publish(db, job_id, "ERROR", f"Job {job_id} failed: {e}")
    finally:
        db.close()

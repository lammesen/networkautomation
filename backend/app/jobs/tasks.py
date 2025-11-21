"""Celery tasks for network automation jobs."""

from __future__ import annotations

import hashlib
from datetime import datetime

from celery import shared_task

from app.automation import (
    AutomationContext,
    run_commands_task,
    get_config_task,
    load_merge_config_task,
    load_replace_config_task,
    validate_task,
)
from app.core.logging import get_logger
from app.db import ConfigSnapshot, Device, SessionLocal
from app.services.job_service import JobService

logger = get_logger(__name__)


def _derive_status(success: int, failed: int) -> str:
    if failed == 0:
        return "success"
    if success == 0:
        return "failed"
    return "partial"


class JobExecution:
    """Context manager for Celery job runs."""

    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.db = SessionLocal()
        self.job_service = JobService(self.db)

    def __enter__(self) -> "JobExecution":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.db.close()

    @property
    def session(self):
        return self.db

    def start(self, message: str) -> None:
        self.job_service.set_status(self.job_id, "running")
        self.log("INFO", message)

    def log(self, level: str, message: str, host: str | None = None, extra: dict | None = None) -> None:
        self.job_service.append_log(
            self.job_id,
            level=level,
            message=message,
            host=host,
            extra=extra,
        )

    def complete(self, status: str, summary: dict, message: str | None = None) -> None:
        self.job_service.set_status(self.job_id, status, summary)
        if message:
            self.log("INFO", message)

    def fail(self, error_message: str) -> None:
        self.log("ERROR", f"Job failed with error: {error_message}")
        self.job_service.set_status(self.job_id, "failed", {"error": error_message})

    def automation(self, targets: dict) -> AutomationContext:
        return AutomationContext(
            job_id=self.job_id,
            targets=targets,
            job_service=self.job_service,
        )


@shared_task(name="run_commands_job")
def run_commands_job(job_id: int, targets: dict, commands: list[str], timeout: int = 30) -> None:
    """Execute commands on target devices."""
    with JobExecution(job_id) as job:
        try:
            job.start("Starting command execution on target devices")
            ctx = job.automation(targets)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices")

            if not device_ids:
                job.fail("No devices matched filters")
                return

            nr = ctx.nornir()
            results = nr.run(task=run_commands_task, commands=commands)

            success_count = 0
            failed_count = 0
            device_results = {}

            for host, result in results.items():
                if result.failed:
                    failed_count += 1
                    ctx.log("ERROR", f"Failed on device {host}", host=host)
                    device_results[host] = {
                        "status": "failed",
                        "error": str(result.exception),
                    }
                else:
                    success_count += 1
                    ctx.log("INFO", f"Completed on device {host}", host=host)
                    device_results[host] = {
                        "status": "success",
                        "results": result.result,
                    }

            status = _derive_status(success_count, failed_count)
            summary = {
                "total": len(device_ids),
                "success": success_count,
                "failed": failed_count,
                "results": device_results,
            }
            job.complete(
                status,
                summary,
                f"Job completed: {success_count} success, {failed_count} failed",
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error in run_commands_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="config_backup_job")
def config_backup_job(job_id: int, targets: dict, source_label: str = "manual") -> None:
    """Backup configurations from target devices."""
    with JobExecution(job_id) as job:
        try:
            job.start("Starting configuration backup")
            ctx = job.automation(targets)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices")

            if not device_ids:
                job.fail("No devices matched filters")
                return

            nr = ctx.nornir()
            results = nr.run(task=get_config_task, retrieve="running")

            success_count = 0
            failed_count = 0
            changed_count = 0

            for host, result in results.items():
                device = (
                    job.session.query(Device).filter(Device.hostname == host).first()
                )
                if not device:
                    continue

                if result.failed:
                    failed_count += 1
                    ctx.log("ERROR", f"Failed to backup {host}", host=host)
                    continue

                config_text = result.result
                config_hash = hashlib.sha256(config_text.encode()).hexdigest()

                last_snapshot = (
                    job.session.query(ConfigSnapshot)
                    .filter(ConfigSnapshot.device_id == device.id)
                    .order_by(ConfigSnapshot.created_at.desc())
                    .first()
                )

                if not last_snapshot or last_snapshot.hash != config_hash:
                    snapshot = ConfigSnapshot(
                        device_id=device.id,
                        job_id=job_id,
                        source=source_label,
                        config_text=config_text,
                        hash=config_hash,
                        created_at=datetime.utcnow(),
                    )
                    job.session.add(snapshot)
                    job.session.commit()
                    changed_count += 1
                    ctx.log(
                        "INFO",
                        f"Config changed on {host}, snapshot saved",
                        host=host,
                    )
                else:
                    ctx.log("INFO", f"No config change on {host}", host=host)

                success_count += 1

            status = _derive_status(success_count, failed_count)
            summary = {
                "total": len(device_ids),
                "success": success_count,
                "failed": failed_count,
                "changed": changed_count,
            }
            job.complete(
                status,
                summary,
                f"Backup completed: {success_count} success, {changed_count} changed",
            )
        except Exception as exc:
            logger.exception("Error in config_backup_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="config_deploy_preview_job")
def config_deploy_preview_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    """Preview configuration deployment."""
    with JobExecution(job_id) as job:
        try:
            job.start(f"Starting config deployment preview ({mode} mode)")
            ctx = job.automation(targets)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices")

            if not device_ids:
                job.fail("No devices matched filters")
                return

            nr = ctx.nornir()
            if mode == "merge":
                results = nr.run(task=load_merge_config_task, config=snippet, dry_run=True)
            else:
                results = nr.run(task=load_replace_config_task, config=snippet, dry_run=True)

            success_count = 0
            failed_count = 0
            diffs = {}

            for host, result in results.items():
                if result.failed:
                    failed_count += 1
                    ctx.log("ERROR", f"Failed to preview on {host}", host=host)
                    diffs[host] = {"status": "failed", "error": str(result.exception)}
                else:
                    success_count += 1
                    diff_text = result.diff or "No changes"
                    ctx.log("INFO", f"Preview completed on {host}", host=host)
                    diffs[host] = {"status": "success", "diff": diff_text}

            status = _derive_status(success_count, failed_count)
            summary = {
                "total": len(device_ids),
                "success": success_count,
                "failed": failed_count,
                "diffs": diffs,
            }
            job.complete(
                status,
                summary,
                f"Preview completed: {success_count} success, {failed_count} failed",
            )
        except Exception as exc:
            logger.exception("Error in config_deploy_preview_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="config_deploy_commit_job")
def config_deploy_commit_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    """Commit configuration deployment."""
    with JobExecution(job_id) as job:
        try:
            job.start(f"Starting config deployment commit ({mode} mode)")
            ctx = job.automation(targets)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices")

            if not device_ids:
                job.fail("No devices matched filters")
                return

            nr = ctx.nornir()
            if mode == "merge":
                results = nr.run(task=load_merge_config_task, config=snippet, dry_run=False)
            else:
                results = nr.run(task=load_replace_config_task, config=snippet, dry_run=False)

            success_count = 0
            failed_count = 0
            commit_results = {}

            for host, result in results.items():
                if result.failed:
                    failed_count += 1
                    ctx.log("ERROR", f"Failed to commit on {host}", host=host)
                    commit_results[host] = {
                        "status": "failed",
                        "error": str(result.exception),
                    }
                else:
                    success_count += 1
                    ctx.log("INFO", f"Successfully committed on {host}", host=host)
                    commit_results[host] = {"status": "success"}

            status = _derive_status(success_count, failed_count)
            summary = {
                "total": len(device_ids),
                "success": success_count,
                "failed": failed_count,
                "results": commit_results,
            }
            job.complete(
                status,
                summary,
                f"Commit completed: {success_count} success, {failed_count} failed",
            )
        except Exception as exc:
            logger.exception("Error in config_deploy_commit_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="compliance_check_job")
def compliance_check_job(job_id: int, policy_id: int) -> None:
    """Run compliance check for a policy."""
    from app.db import CompliancePolicy, ComplianceResult

    with JobExecution(job_id) as job:
        try:
            job.start("Starting compliance check")
            policy = (
                job.session.query(CompliancePolicy)
                .filter(CompliancePolicy.id == policy_id)
                .first()
            )

            if not policy:
                job.fail("Policy not found")
                return

            ctx = job.automation(policy.scope_json)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices")

            if not device_ids:
                job.fail("No devices matched policy scope")
                return

            nr = ctx.nornir()
            results = nr.run(task=validate_task, validation_source=policy.definition_yaml)

            pass_count = 0
            fail_count = 0
            error_count = 0

            for host, result in results.items():
                device = (
                    job.session.query(Device).filter(Device.hostname == host).first()
                )
                if not device:
                    continue

                if result.failed:
                    error_count += 1
                    status = "error"
                    details = {"error": str(result.exception)}
                    ctx.log("ERROR", f"Validation error on {host}", host=host)
                else:
                    validation_result = result.result
                    complies = validation_result.get("complies", False)
                    details = validation_result
                    if complies:
                        pass_count += 1
                        status = "pass"
                        ctx.log("INFO", f"Compliance check passed on {host}", host=host)
                    else:
                        fail_count += 1
                        status = "fail"
                        ctx.log("WARN", f"Compliance check failed on {host}", host=host)

                compliance_result = ComplianceResult(
                    policy_id=policy_id,
                    device_id=device.id,
                    job_id=job_id,
                    ts=datetime.utcnow(),
                    status=status,
                    details_json=details,
                )
                job.session.add(compliance_result)

            job.session.commit()

            status = "success" if error_count == 0 else "partial"
            summary = {
                "total": len(device_ids),
                "pass": pass_count,
                "fail": fail_count,
                "error": error_count,
            }
            job.complete(
                status,
                summary,
                f"Compliance check completed: {pass_count} pass, {fail_count} fail",
            )
        except Exception as exc:
            logger.exception("Error in compliance_check_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="scheduled_config_backup")
def scheduled_config_backup() -> None:
    """Scheduled task to backup all enabled devices daily."""
    from app.db import User
    
    db = SessionLocal()
    
    try:
        # Get system user for scheduled jobs
        system_user = db.query(User).filter(User.username == "admin").first()
        if not system_user:
            logger.error("No admin user found for scheduled backup")
            return
        
        # Create job for scheduled backup
        from app.jobs.manager import create_job
        job = create_job(
            db=db,
            job_type="config_backup",
            user=system_user,
            target_summary={"filters": {}, "source": "scheduled"},
            payload={"source_label": "scheduled"},
        )
        
        logger.info(f"Created scheduled backup job {job.id}")
        
        # Run the backup job
        config_backup_job(job.id, {}, "scheduled")
        
    except Exception as e:
        logger.exception(f"Error in scheduled_config_backup: {e}")
    finally:
        db.close()


@shared_task(name="check_reachability_job")
def check_reachability_job() -> None:
    """Check reachability (SSH port open) for all enabled devices."""
    import socket
    from app.db import Device
    
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.enabled == True).all()
        logger.info(f"Checking reachability for {len(devices)} devices")
        
        for device in devices:
            is_reachable = False
            try:
                # Simple TCP connect check to port 22 (or 830/other if needed, but 22 is standard mgmt)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                result = sock.connect_ex((device.mgmt_ip, 22))
                sock.close()
                if result == 0:
                    is_reachable = True
            except Exception:
                pass
            
            status = "reachable" if is_reachable else "unreachable"
            
            # Update DB
            device.reachability_status = status
            device.last_reachability_check = datetime.utcnow()
            
        db.commit()
        logger.info("Reachability check completed")
        
    except Exception as e:
        logger.exception(f"Error in check_reachability_job: {e}")
    finally:
        db.close()

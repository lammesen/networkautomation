"""Celery tasks for network automation jobs."""

from celery import shared_task
from datetime import datetime
import hashlib

from app.db import SessionLocal, Device, ConfigSnapshot
from app.jobs.manager import update_job_status, create_job_log
from app.automation import (
    init_nornir,
    filter_nornir_hosts,
    filter_devices_from_db,
    run_commands_task,
    get_config_task,
    load_merge_config_task,
    load_replace_config_task,
    validate_task,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(name="run_commands_job")
def run_commands_job(job_id: int, targets: dict, commands: list[str], timeout: int = 30) -> None:
    """Execute commands on target devices."""
    db = SessionLocal()
    
    try:
        update_job_status(db, job_id, "running")
        create_job_log(db, job_id, "INFO", f"Starting command execution on target devices")
        
        # Filter devices
        device_ids = filter_devices_from_db(targets)
        create_job_log(db, job_id, "INFO", f"Found {len(device_ids)} target devices")
        
        if not device_ids:
            update_job_status(db, job_id, "failed", {"error": "No devices matched filters"})
            return
        
        # Initialize Nornir
        nr = init_nornir()
        nr = filter_nornir_hosts(nr, device_ids)
        
        # Run commands
        results = nr.run(task=run_commands_task, commands=commands)
        
        # Process results
        success_count = 0
        failed_count = 0
        device_results = {}
        
        for host, result in results.items():
            if result.failed:
                failed_count += 1
                create_job_log(db, job_id, "ERROR", f"Failed on device {host}", host=host)
                device_results[host] = {"status": "failed", "error": str(result.exception)}
            else:
                success_count += 1
                create_job_log(db, job_id, "INFO", f"Completed on device {host}", host=host)
                device_results[host] = {"status": "success", "results": result.result}
        
        # Update job
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        summary = {
            "total": len(device_ids),
            "success": success_count,
            "failed": failed_count,
            "results": device_results,
        }
        update_job_status(db, job_id, status, summary)
        create_job_log(db, job_id, "INFO", f"Job completed: {success_count} success, {failed_count} failed")
        
    except Exception as e:
        logger.exception(f"Error in run_commands_job {job_id}")
        create_job_log(db, job_id, "ERROR", f"Job failed with error: {str(e)}")
        update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()


@shared_task(name="config_backup_job")
def config_backup_job(job_id: int, targets: dict, source_label: str = "manual") -> None:
    """Backup configurations from target devices."""
    db = SessionLocal()
    
    try:
        update_job_status(db, job_id, "running")
        create_job_log(db, job_id, "INFO", "Starting configuration backup")
        
        # Filter devices
        device_ids = filter_devices_from_db(targets)
        create_job_log(db, job_id, "INFO", f"Found {len(device_ids)} target devices")
        
        if not device_ids:
            update_job_status(db, job_id, "failed", {"error": "No devices matched filters"})
            return
        
        # Initialize Nornir
        nr = init_nornir()
        nr = filter_nornir_hosts(nr, device_ids)
        
        # Get configurations
        results = nr.run(task=get_config_task, retrieve="running")
        
        # Process results
        success_count = 0
        failed_count = 0
        changed_count = 0
        
        for host, result in results.items():
            device = db.query(Device).filter(Device.hostname == host).first()
            if not device:
                continue
            
            if result.failed:
                failed_count += 1
                create_job_log(db, job_id, "ERROR", f"Failed to backup {host}", host=host)
                continue
            
            config_text = result.result
            config_hash = hashlib.sha256(config_text.encode()).hexdigest()
            
            # Check if config changed
            last_snapshot = (
                db.query(ConfigSnapshot)
                .filter(ConfigSnapshot.device_id == device.id)
                .order_by(ConfigSnapshot.created_at.desc())
                .first()
            )
            
            if not last_snapshot or last_snapshot.hash != config_hash:
                # Config changed, save snapshot
                snapshot = ConfigSnapshot(
                    device_id=device.id,
                    job_id=job_id,
                    source=source_label,
                    config_text=config_text,
                    hash=config_hash,
                    created_at=datetime.utcnow(),
                )
                db.add(snapshot)
                db.commit()
                changed_count += 1
                create_job_log(db, job_id, "INFO", f"Config changed on {host}, snapshot saved", host=host)
            else:
                create_job_log(db, job_id, "INFO", f"No config change on {host}", host=host)
            
            success_count += 1
        
        # Update job
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        summary = {
            "total": len(device_ids),
            "success": success_count,
            "failed": failed_count,
            "changed": changed_count,
        }
        update_job_status(db, job_id, status, summary)
        create_job_log(db, job_id, "INFO", f"Backup completed: {success_count} success, {changed_count} changed")
        
    except Exception as e:
        logger.exception(f"Error in config_backup_job {job_id}")
        create_job_log(db, job_id, "ERROR", f"Job failed with error: {str(e)}")
        update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()


@shared_task(name="config_deploy_preview_job")
def config_deploy_preview_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    """Preview configuration deployment."""
    db = SessionLocal()
    
    try:
        update_job_status(db, job_id, "running")
        create_job_log(db, job_id, "INFO", f"Starting config deployment preview ({mode} mode)")
        
        # Filter devices
        device_ids = filter_devices_from_db(targets)
        create_job_log(db, job_id, "INFO", f"Found {len(device_ids)} target devices")
        
        if not device_ids:
            update_job_status(db, job_id, "failed", {"error": "No devices matched filters"})
            return
        
        # Initialize Nornir
        nr = init_nornir()
        nr = filter_nornir_hosts(nr, device_ids)
        
        # Load config and get diff
        if mode == "merge":
            results = nr.run(task=load_merge_config_task, config=snippet, dry_run=True)
        else:
            results = nr.run(task=load_replace_config_task, config=snippet, dry_run=True)
        
        # Process results
        success_count = 0
        failed_count = 0
        diffs = {}
        
        for host, result in results.items():
            if result.failed:
                failed_count += 1
                create_job_log(db, job_id, "ERROR", f"Failed to preview on {host}", host=host)
                diffs[host] = {"status": "failed", "error": str(result.exception)}
            else:
                success_count += 1
                diff_text = result.diff or "No changes"
                create_job_log(db, job_id, "INFO", f"Preview completed on {host}", host=host)
                diffs[host] = {"status": "success", "diff": diff_text}
        
        # Update job
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        summary = {
            "total": len(device_ids),
            "success": success_count,
            "failed": failed_count,
            "diffs": diffs,
        }
        update_job_status(db, job_id, status, summary)
        create_job_log(db, job_id, "INFO", f"Preview completed: {success_count} success, {failed_count} failed")
        
    except Exception as e:
        logger.exception(f"Error in config_deploy_preview_job {job_id}")
        create_job_log(db, job_id, "ERROR", f"Job failed with error: {str(e)}")
        update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()


@shared_task(name="config_deploy_commit_job")
def config_deploy_commit_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    """Commit configuration deployment."""
    db = SessionLocal()
    
    try:
        update_job_status(db, job_id, "running")
        create_job_log(db, job_id, "INFO", f"Starting config deployment commit ({mode} mode)")
        
        # Filter devices
        device_ids = filter_devices_from_db(targets)
        create_job_log(db, job_id, "INFO", f"Found {len(device_ids)} target devices")
        
        if not device_ids:
            update_job_status(db, job_id, "failed", {"error": "No devices matched filters"})
            return
        
        # Initialize Nornir
        nr = init_nornir()
        nr = filter_nornir_hosts(nr, device_ids)
        
        # Load config and commit
        if mode == "merge":
            results = nr.run(task=load_merge_config_task, config=snippet, dry_run=False)
        else:
            results = nr.run(task=load_replace_config_task, config=snippet, dry_run=False)
        
        # Process results
        success_count = 0
        failed_count = 0
        commit_results = {}
        
        for host, result in results.items():
            if result.failed:
                failed_count += 1
                create_job_log(db, job_id, "ERROR", f"Failed to commit on {host}", host=host)
                commit_results[host] = {"status": "failed", "error": str(result.exception)}
            else:
                success_count += 1
                create_job_log(db, job_id, "INFO", f"Successfully committed on {host}", host=host)
                commit_results[host] = {"status": "success"}
        
        # Update job
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        summary = {
            "total": len(device_ids),
            "success": success_count,
            "failed": failed_count,
            "results": commit_results,
        }
        update_job_status(db, job_id, status, summary)
        create_job_log(db, job_id, "INFO", f"Commit completed: {success_count} success, {failed_count} failed")
        
    except Exception as e:
        logger.exception(f"Error in config_deploy_commit_job {job_id}")
        create_job_log(db, job_id, "ERROR", f"Job failed with error: {str(e)}")
        update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()


@shared_task(name="compliance_check_job")
def compliance_check_job(job_id: int, policy_id: int) -> None:
    """Run compliance check for a policy."""
    db = SessionLocal()
    
    try:
        from app.db import CompliancePolicy, ComplianceResult
        
        update_job_status(db, job_id, "running")
        create_job_log(db, job_id, "INFO", "Starting compliance check")
        
        # Get policy
        policy = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()
        if not policy:
            update_job_status(db, job_id, "failed", {"error": "Policy not found"})
            return
        
        # Filter devices based on policy scope
        device_ids = filter_devices_from_db(policy.scope_json)
        create_job_log(db, job_id, "INFO", f"Found {len(device_ids)} target devices")
        
        if not device_ids:
            update_job_status(db, job_id, "failed", {"error": "No devices matched policy scope"})
            return
        
        # Initialize Nornir
        nr = init_nornir()
        nr = filter_nornir_hosts(nr, device_ids)
        
        # Run validation
        results = nr.run(task=validate_task, validation_source=policy.definition_yaml)
        
        # Process results
        pass_count = 0
        fail_count = 0
        error_count = 0
        
        for host, result in results.items():
            device = db.query(Device).filter(Device.hostname == host).first()
            if not device:
                continue
            
            if result.failed:
                error_count += 1
                status = "error"
                details = {"error": str(result.exception)}
                create_job_log(db, job_id, "ERROR", f"Validation error on {host}", host=host)
            else:
                validation_result = result.result
                complies = validation_result.get("complies", False)
                if complies:
                    pass_count += 1
                    status = "pass"
                    create_job_log(db, job_id, "INFO", f"Compliance check passed on {host}", host=host)
                else:
                    fail_count += 1
                    status = "fail"
                    create_job_log(db, job_id, "WARN", f"Compliance check failed on {host}", host=host)
                details = validation_result
            
            # Save result
            compliance_result = ComplianceResult(
                policy_id=policy_id,
                device_id=device.id,
                job_id=job_id,
                ts=datetime.utcnow(),
                status=status,
                details_json=details,
            )
            db.add(compliance_result)
        
        db.commit()
        
        # Update job
        status = "success" if error_count == 0 else "partial"
        summary = {
            "total": len(device_ids),
            "pass": pass_count,
            "fail": fail_count,
            "error": error_count,
        }
        update_job_status(db, job_id, status, summary)
        create_job_log(db, job_id, "INFO", f"Compliance check completed: {pass_count} pass, {fail_count} fail")
        
    except Exception as e:
        logger.exception(f"Error in compliance_check_job {job_id}")
        create_job_log(db, job_id, "ERROR", f"Job failed with error: {str(e)}")
        update_job_status(db, job_id, "failed", {"error": str(e)})
    finally:
        db.close()


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

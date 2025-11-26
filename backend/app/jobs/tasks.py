"""Celery tasks for network automation jobs."""

from __future__ import annotations

import hashlib
from datetime import datetime

from celery import shared_task
from napalm import get_network_driver

from app.automation import (
    AutomationContext,
    get_config_task,
    load_merge_config_task,
    load_replace_config_task,
    run_commands_task,
    validate_task,
)
from app.automation.tasks_topology import discover_neighbors_task
from app.core.crypto import decrypt_text
from app.core.logging import get_logger
from app.db import ConfigSnapshot, Device, Job, SessionLocal, TopologyLink
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
        self.job_record: Job | None = None

    def __enter__(self) -> "JobExecution":
        self.job_record = self.job_service.jobs.get_by_id(self.job_id)
        if not self.job_record:
            raise RuntimeError(f"Job {self.job_id} not found")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.db.close()

    @property
    def session(self):
        return self.db

    def start(self, message: str) -> None:
        self.job_service.set_status(self.job_id, "running")
        self.log("INFO", message)

    def log(
        self, level: str, message: str, host: str | None = None, extra: dict | None = None
    ) -> None:
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
            customer_id=self.job_record.customer_id if self.job_record else None,
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
                device = job.session.query(Device).filter(Device.hostname == host).first()
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


@shared_task(name="config_rollback_preview_job")
def config_rollback_preview_job(job_id: int, device_id: int, target_config: str) -> None:
    """Preview configuration rollback to a previous snapshot.

    Loads the target configuration in replace mode with dry_run=True to show
    what would change when rolling back.
    """
    with JobExecution(job_id) as job:
        try:
            job.start("Starting rollback preview")

            # Get the device to build single-device target
            device = job.session.query(Device).filter(Device.id == device_id).first()
            if not device:
                job.fail("Device not found")
                return

            ctx = job.automation({"device_ids": [device_id]})
            device_ids = ctx.select_devices()

            if not device_ids:
                job.fail("Device not found or not accessible")
                return

            ctx.log("INFO", f"Previewing rollback for device: {device.hostname}")

            nr = ctx.nornir()
            results = nr.run(task=load_replace_config_task, config=target_config, dry_run=True)

            for host, result in results.items():
                if result.failed:
                    job.fail(f"Failed to preview on {host}: {result.exception}")
                    return

                diff_text = result.diff or "No changes (config identical to snapshot)"
                ctx.log("INFO", f"Rollback preview completed on {host}", host=host)

                summary = {
                    "device_id": device_id,
                    "hostname": host,
                    "diff": diff_text,
                    "has_changes": bool(result.diff),
                }
                job.complete("success", summary, "Rollback preview completed successfully")
                return

            job.fail("No results from rollback preview")
        except Exception as exc:
            logger.exception("Error in config_rollback_preview_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="config_rollback_commit_job")
def config_rollback_commit_job(job_id: int, device_id: int, target_config: str) -> None:
    """Commit configuration rollback.

    Replaces the device configuration with the snapshot configuration.
    Automatically creates a backup of the current config before rollback.
    """
    with JobExecution(job_id) as job:
        try:
            job.start("Starting rollback commit")

            device = job.session.query(Device).filter(Device.id == device_id).first()
            if not device:
                job.fail("Device not found")
                return

            ctx = job.automation({"device_ids": [device_id]})
            device_ids = ctx.select_devices()

            if not device_ids:
                job.fail("Device not found or not accessible")
                return

            hostname = device.hostname
            ctx.log("INFO", f"Backing up current config before rollback on {hostname}")

            nr = ctx.nornir()

            # First, backup current config before rollback
            backup_results = nr.run(task=get_config_task, retrieve="running")
            for host, result in backup_results.items():
                if result.failed:
                    ctx.log(
                        "WARN",
                        f"Could not backup current config on {host}: {result.exception}",
                        host=host,
                    )
                else:
                    # Save pre-rollback snapshot
                    config_text = result.result
                    config_hash = hashlib.sha256(config_text.encode()).hexdigest()
                    pre_rollback_snapshot = ConfigSnapshot(
                        device_id=device_id,
                        job_id=job_id,
                        source="pre-rollback",
                        config_text=config_text,
                        hash=config_hash,
                        created_at=datetime.utcnow(),
                    )
                    job.session.add(pre_rollback_snapshot)
                    job.session.commit()
                    ctx.log("INFO", f"Pre-rollback backup saved for {host}", host=host)

            # Now perform the rollback
            ctx.log("INFO", f"Applying rollback configuration on {hostname}")
            results = nr.run(task=load_replace_config_task, config=target_config, dry_run=False)

            for host, result in results.items():
                if result.failed:
                    job.fail(f"Failed to apply rollback on {host}: {result.exception}")
                    return

                ctx.log("INFO", f"Rollback completed successfully on {host}", host=host)

                # Save post-rollback snapshot
                post_backup_results = nr.run(task=get_config_task, retrieve="running")
                for post_host, post_result in post_backup_results.items():
                    if not post_result.failed:
                        post_config = post_result.result
                        post_hash = hashlib.sha256(post_config.encode()).hexdigest()
                        post_rollback_snapshot = ConfigSnapshot(
                            device_id=device_id,
                            job_id=job_id,
                            source="post-rollback",
                            config_text=post_config,
                            hash=post_hash,
                            created_at=datetime.utcnow(),
                        )
                        job.session.add(post_rollback_snapshot)
                        job.session.commit()
                        ctx.log("INFO", f"Post-rollback snapshot saved for {post_host}")

                summary = {
                    "device_id": device_id,
                    "hostname": host,
                    "status": "success",
                }
                job.complete("success", summary, "Rollback committed successfully")
                return

            job.fail("No results from rollback commit")
        except Exception as exc:
            logger.exception("Error in config_rollback_commit_job %s", job_id)
            job.fail(str(exc))


@shared_task(name="compliance_check_job")
def compliance_check_job(job_id: int, policy_id: int) -> None:
    """Run compliance check for a policy."""
    from app.db import CompliancePolicy, ComplianceResult

    with JobExecution(job_id) as job:
        try:
            job.start("Starting compliance check")
            policy = (
                job.session.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()
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
                device = job.session.query(Device).filter(Device.hostname == host).first()
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
    from app.db import Customer, User

    db = SessionLocal()

    try:
        # Get system user for scheduled jobs
        system_user = db.query(User).filter(User.username == "admin").first()
        if not system_user:
            logger.error("No admin user found for scheduled backup")
            return

        customers = db.query(Customer).all()
        if not customers:
            logger.info("No customers found; skipping scheduled backup")
            return

        from app.jobs.manager import create_job

        for customer in customers:
            job = create_job(
                db=db,
                job_type="config_backup",
                user=system_user,
                customer_id=customer.id,
                target_summary={"filters": {}, "source": "scheduled"},
                payload={"source_label": "scheduled"},
            )

            logger.info("Created scheduled backup job %s for customer %s", job.id, customer.id)

            # Run the backup job
            config_backup_job(job.id, {"customer_id": customer.id}, "scheduled")

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
        devices = db.query(Device).filter(Device.enabled.is_(True)).all()
        logger.info(f"Checking reachability for {len(devices)} devices")

        for device in devices:
            is_reachable = False
            try:
                addr = device.mgmt_ip
                with socket.create_connection((addr, 22), timeout=2.0):
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


@shared_task(name="refresh_device_info")
def refresh_device_info(device_id: int) -> None:
    """Fetch basic facts from a device and store them on the record."""
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return
        cred = device.credential
        if not cred:
            return

        username = cred.username
        password = decrypt_text(cred.password)
        enable = decrypt_text(cred.enable_password) or password

        driver_map = {
            ("cisco", "ios"): "ios",
            ("cisco", "iosxe"): "ios",
            ("cisco", "iosxr"): "iosxr",
            ("cisco", "nxos"): "nxos",
            ("arista", "eos"): "eos",
            ("juniper", "junos"): "junos",
            ("linux", "linux"): "linux",
        }
        napalm_driver = driver_map.get((device.vendor.lower(), device.platform.lower()), "ios")

        driver = get_network_driver(napalm_driver)
        optional_args = {}
        if enable:
            optional_args["secret"] = enable

        facts = {}
        try:
            with driver(
                hostname=device.mgmt_ip,
                username=username,
                password=password,
                optional_args=optional_args,
            ) as nap:
                facts = nap.get_facts()
        except Exception as exc:
            logger.warning("refresh_device_info failed for %s: %s", device.hostname, exc)
            return

        tags = device.tags or {}
        tags["facts"] = {
            "vendor": facts.get("vendor"),
            "model": facts.get("model"),
            "os_version": facts.get("os_version"),
            "serial_number": facts.get("serial_number"),
            "uptime": facts.get("uptime"),
            "hostname": facts.get("hostname"),
        }
        device.tags = tags
        db.add(device)
        db.commit()
    finally:
        db.close()


@shared_task(name="topology_discovery_job")
def topology_discovery_job(job_id: int, targets: dict) -> None:
    """Discover network topology using CDP/LLDP neighbors."""
    with JobExecution(job_id) as job:
        try:
            job.start("Starting topology discovery")

            ctx = job.automation(targets)
            device_ids = ctx.select_devices()
            ctx.log("INFO", f"Found {len(device_ids)} target devices for discovery")

            if not device_ids:
                job.fail("No devices matched the target filters")
                return

            nr = ctx.nornir()
            results = nr.run(task=discover_neighbors_task)

            total_links = 0
            success_count = 0
            error_count = 0

            # Build hostname -> device_id mapping for linking
            hostname_to_device: dict[str, int] = {}
            for device_id in device_ids:
                device = job.session.query(Device).filter(Device.id == device_id).first()
                if device:
                    hostname_to_device[device.hostname.lower()] = device.id

            for host, result in results.items():
                device = job.session.query(Device).filter(Device.hostname == host).first()
                if not device:
                    ctx.log("WARN", f"Device {host} not found in database", host=host)
                    continue

                if result.failed:
                    error_count += 1
                    ctx.log(
                        "ERROR",
                        f"Discovery failed on {host}: {result.exception}",
                        host=host,
                    )
                    continue

                discovery_result = result.result
                neighbors = discovery_result.get("neighbors", {})
                lldp_neighbors = neighbors.get("lldp", [])

                ctx.log(
                    "INFO",
                    f"Found {len(lldp_neighbors)} neighbors on {host}",
                    host=host,
                )

                for neighbor in lldp_neighbors:
                    # Try to match remote hostname to a known device
                    remote_hostname = neighbor.get("remote_hostname", "unknown")
                    remote_device_id = hostname_to_device.get(remote_hostname.lower())

                    # Create or update the topology link
                    existing = (
                        job.session.query(TopologyLink)
                        .filter(
                            TopologyLink.customer_id == device.customer_id,
                            TopologyLink.local_device_id == device.id,
                            TopologyLink.local_interface == neighbor["local_interface"],
                            TopologyLink.remote_hostname == remote_hostname,
                        )
                        .first()
                    )

                    if existing:
                        # Update existing link
                        existing.remote_interface = neighbor.get("remote_interface", "unknown")
                        existing.remote_ip = neighbor.get("remote_ip", "")
                        existing.remote_platform = neighbor.get("remote_platform", "")
                        existing.remote_device_id = remote_device_id
                        existing.discovered_at = datetime.utcnow()
                        existing.job_id = job_id
                    else:
                        # Create new link
                        link = TopologyLink(
                            customer_id=device.customer_id,
                            local_device_id=device.id,
                            local_interface=neighbor["local_interface"],
                            remote_device_id=remote_device_id,
                            remote_hostname=remote_hostname,
                            remote_interface=neighbor.get("remote_interface", "unknown"),
                            remote_ip=neighbor.get("remote_ip", ""),
                            remote_platform=neighbor.get("remote_platform", ""),
                            protocol=neighbor.get("protocol", "lldp"),
                            discovered_at=datetime.utcnow(),
                            job_id=job_id,
                        )
                        job.session.add(link)

                    total_links += 1

                success_count += 1

            job.session.commit()

            status = _derive_status(success_count, error_count)
            summary = {
                "devices_scanned": len(device_ids),
                "devices_success": success_count,
                "devices_failed": error_count,
                "links_discovered": total_links,
            }
            job.complete(
                status,
                summary,
                f"Topology discovery completed: {total_links} links from {success_count} devices",
            )

        except Exception as exc:
            logger.exception("Error in topology_discovery_job %s", job_id)
            job.fail(str(exc))

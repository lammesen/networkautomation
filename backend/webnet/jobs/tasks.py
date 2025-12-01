"""Celery tasks for webnet automation.

These tasks run Nornir drivers (netmiko/napalm) where possible. If a host
fails, we log and continue so multi-host jobs can be partial-success.
"""

from __future__ import annotations

import logging
import re

from celery import shared_task

try:  # pragma: no cover - optional dependency
    from nornir.core import Nornir
    from nornir.core.plugins.runners import ThreadedRunner
except ImportError:  # pragma: no cover - fallback for tests

    class Nornir:  # type: ignore
        def __init__(self, inventory=None, runner=None):
            self.inventory = inventory
            self.runner = runner

    class ThreadedRunner:  # type: ignore
        pass


try:  # pragma: no cover - optional dependency
    from nornir_netmiko.tasks import netmiko_send_command
except ImportError:  # pragma: no cover - fallback for tests

    def netmiko_send_command(*args, **kwargs):  # type: ignore
        return None


try:  # pragma: no cover - optional dependency
    from nornir_napalm.tasks import napalm_get, napalm_configure
except ImportError:  # pragma: no cover - fallback for tests

    def napalm_get(*args, **kwargs):  # type: ignore
        return None

    def napalm_configure(*args, **kwargs):  # type: ignore
        return None


from webnet.jobs.models import Job
from webnet.jobs.services import JobService
from webnet.automation import build_inventory
from webnet.devices.models import Device, TopologyLink
from webnet.config_mgmt.models import ConfigSnapshot

logger = logging.getLogger(__name__)


def _nr_from_inventory(inv) -> Nornir:
    return Nornir(inventory=inv, runner=ThreadedRunner())


def _log_host_result(js: JobService, job: Job, host: str, result) -> None:
    if result.failed:
        js.append_log(job, level="ERROR", host=host, message=str(result.exception or result.result))
    else:
        js.append_log(job, level="INFO", host=host, message=str(result.result))


@shared_task(name="run_commands_job")
def run_commands_job(job_id: int, targets: dict, commands: list[str], timeout: int = 30) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:  # pragma: no cover - defensive
        logger.warning("Job %s not found for run_commands", job_id)
        return
    js.set_status(job, "running")
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    nr = _nr_from_inventory(inventory)
    try:
        for cmd in commands:
            res = nr.run(netmiko_send_command, command_string=cmd, timeout=timeout)
            for host, r in res.items():
                _log_host_result(js, job, host, r)
        js.set_status(
            job, "success", result_summary={"commands": len(commands), "targets": targets}
        )
    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="config_backup_job")
def config_backup_job(
    job_id: int, targets: dict, source_label: str = "manual", auto_git_sync: bool = True
) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    nr = _nr_from_inventory(inventory)
    snapshot_ids: list[int] = []
    try:
        res = nr.run(napalm_get, getters=["config"])
        for host, r in res.items():
            if r.failed:
                _log_host_result(js, job, host, r)
                continue
            cfg = (r.result.get("config") or {}).get("running") or ""
            js.append_log(
                job, level="INFO", host=host, message=f"Backed up config ({len(cfg)} bytes)"
            )
            device = Device.objects.filter(hostname=host, customer=job.customer).first()
            if device:
                snapshot = ConfigSnapshot.objects.create(
                    device=device,
                    job=job,
                    source=source_label,
                    config_text=cfg,
                )
                snapshot_ids.append(snapshot.id)
        js.set_status(job, "success", result_summary={"targets": targets})

        # Auto-sync to Git if enabled
        if auto_git_sync and snapshot_ids:
            git_sync_job.delay(job.customer_id, snapshot_ids, job_id)
            js.append_log(job, level="INFO", message="Queued Git sync for backed up configs")

    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="git_sync_job")
def git_sync_job(
    customer_id: int, snapshot_ids: list[int] | None = None, triggering_job_id: int | None = None
) -> dict:
    """Sync config snapshots to the configured Git repository.

    Args:
        customer_id: Customer ID to sync configs for
        snapshot_ids: Optional list of specific snapshot IDs to sync.
                      If None, syncs all unsynced snapshots for the customer.
        triggering_job_id: Optional job ID that triggered this sync (for audit trail)

    Returns:
        Dict with sync result details
    """
    from webnet.config_mgmt.git_service import sync_configs_to_git

    job = None
    if triggering_job_id:
        job = Job.objects.filter(pk=triggering_job_id).first()

    result = sync_configs_to_git(
        customer_id=customer_id,
        snapshot_ids=snapshot_ids,
        job=job,
    )

    return {
        "success": result.success,
        "commit_hash": result.commit_hash,
        "files_synced": result.files_synced,
        "message": result.message,
        "error": result.error,
    }


@shared_task(name="config_deploy_preview_job")
def config_deploy_preview_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    nr = _nr_from_inventory(inventory)
    try:
        res = nr.run(
            napalm_configure, configuration=snippet, dry_run=True, replace=(mode == "replace")
        )
        for host, r in res.items():
            _log_host_result(js, job, host, r)
        js.set_status(job, "success", result_summary={"targets": targets, "mode": mode})
    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="config_deploy_commit_job")
def config_deploy_commit_job(job_id: int, targets: dict, mode: str, snippet: str) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    nr = _nr_from_inventory(inventory)
    try:
        res = nr.run(
            napalm_configure, configuration=snippet, dry_run=False, replace=(mode == "replace")
        )
        for host, r in res.items():
            _log_host_result(js, job, host, r)
        js.set_status(job, "success", result_summary={"targets": targets, "mode": mode})
    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="config_rollback_preview_job")
def config_rollback_preview_job(job_id: int, device_id: int, target_config: str) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    js.append_log(
        job,
        level="ERROR",
        message="Rollback preview not implemented; configure rollback strategy",
    )
    js.set_status(
        job,
        "failed",
        result_summary={"device_id": device_id, "error": "rollback preview not implemented"},
    )


@shared_task(name="config_rollback_commit_job")
def config_rollback_commit_job(job_id: int, device_id: int, target_config: str) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    js.append_log(
        job,
        level="ERROR",
        message="Rollback commit not implemented; configure rollback strategy",
    )
    js.set_status(
        job,
        "failed",
        result_summary={"device_id": device_id, "error": "rollback commit not implemented"},
    )


@shared_task(name="compliance_check_job")
def compliance_check_job(job_id: int, policy_id: int) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    js.append_log(job, level="INFO", message=f"Compliance policy {policy_id} check started")
    js.set_status(job, "success", result_summary={"policy_id": policy_id})


@shared_task(name="scheduled_config_backup")
def scheduled_config_backup() -> None:
    # Placeholder: would enqueue config backup for all customers with schedules
    return


@shared_task(name="check_reachability_job")
def check_reachability_job(job_id: int, targets: dict | None = None) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    try:
        js.set_status(job, "running")
        inventory = build_inventory(targets or {}, customer_id=job.customer_id)
        if not inventory.hosts:
            js.append_log(job, level="ERROR", message="No devices matched targets")
            js.set_status(job, "failed", result_summary={"error": "no devices"})
            return
        nr = _nr_from_inventory(inventory)
        res = nr.run(netmiko_send_command, command_string="ping 127.0.0.1")
        for host, r in res.items():
            _log_host_result(js, job, host, r)
        js.set_status(job, "success", result_summary={"targets": targets or {}})
    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


_def_cdp_device_re = re.compile(r"Device ID\s*:\s*(?P<hostname>\S+)", re.IGNORECASE)
_def_cdp_intf_re = re.compile(
    r"Interface:\s*(?P<local_intf>[^,]+),\s*Port ID \(outgoing port\):\s*(?P<remote_intf>.+)",
    re.IGNORECASE,
)


def _parse_cdp_neighbors(output: str) -> list[dict[str, str]]:
    neighbors: list[dict[str, str]] = []
    if not output:
        return neighbors
    blocks = output.split("\n\n")
    for block in blocks:
        host_match = _def_cdp_device_re.search(block)
        intf_match = _def_cdp_intf_re.search(block)
        if host_match and intf_match:
            neighbors.append(
                {
                    "remote_hostname": host_match.group("hostname").strip(),
                    "local_interface": intf_match.group("local_intf").strip(),
                    "remote_interface": intf_match.group("remote_intf").strip(),
                }
            )
    return neighbors


@shared_task(name="topology_discovery_job")
def topology_discovery_job(job_id: int, targets: dict) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return
    js.set_status(job, "running")
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    nr = _nr_from_inventory(inventory)
    discovered_links = 0
    try:
        res = nr.run(netmiko_send_command, command_string="show cdp neighbors detail")
        for host, r in res.items():
            _log_host_result(js, job, host, r)
            device = Device.objects.filter(hostname=host, customer=job.customer).first()
            if not device or r.failed:
                continue
            neighbors = _parse_cdp_neighbors(str(r.result))
            for n in neighbors:
                remote_dev = Device.objects.filter(
                    customer=device.customer, hostname=n["remote_hostname"]
                ).first()
                _, created = TopologyLink.objects.get_or_create(
                    customer=device.customer,
                    local_device=device,
                    local_interface=n["local_interface"],
                    remote_hostname=n["remote_hostname"],
                    remote_interface=n["remote_interface"],
                    defaults={
                        "remote_device": remote_dev,
                        "remote_ip": None,
                        "remote_platform": remote_dev.platform if remote_dev else None,
                        "protocol": "cdp",
                        "job_id": job.id,
                    },
                )
                if created:
                    discovered_links += 1
        js.set_status(
            job,
            "success",
            result_summary={"targets": targets, "links_created": discovered_links},
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("topology_discovery_job failed for job %s", job_id)
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})

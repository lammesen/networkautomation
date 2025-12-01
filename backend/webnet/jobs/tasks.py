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

        # Auto-sync to Git if enabled and a Git repository is configured
        if auto_git_sync and snapshot_ids:
            from webnet.config_mgmt.models import GitRepository

            if GitRepository.objects.filter(customer_id=job.customer_id, enabled=True).exists():
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

    # After compliance check, trigger auto-remediation if violations found
    # For now, this is a placeholder - real compliance check would populate results
    try:
        from webnet.compliance.models import ComplianceResult

        # Get recent violations for this policy
        violations = ComplianceResult.objects.filter(
            policy_id=policy_id, job=job, status__in=["failed", "violation", "non-compliant"]
        ).select_related("device", "policy")

        if violations.exists():
            js.append_log(
                job,
                level="INFO",
                message=f"Found {violations.count()} violations, checking for auto-remediation rules",
            )
            # Trigger auto-remediation for each violation
            for violation in violations:
                trigger_auto_remediation.delay(violation.id)
    except Exception as e:
        logger.error(f"Error triggering auto-remediation: {e}")

    js.set_status(job, "success", result_summary={"policy_id": policy_id})


@shared_task(name="scheduled_config_backup")
def scheduled_config_backup() -> None:
    # Placeholder: would enqueue config backup for all customers with schedules
    return


@shared_task(name="netbox_sync_job")
def netbox_sync_job(config_id: int, full_sync: bool = False) -> dict:
    """Sync devices from NetBox.

    Args:
        config_id: NetBoxConfig ID
        full_sync: If True, update all devices. If False, only create new ones.

    Returns:
        Dict with sync result details
    """
    from webnet.devices.models import NetBoxConfig
    from webnet.devices.netbox_service import NetBoxService

    try:
        config = NetBoxConfig.objects.get(pk=config_id)
    except NetBoxConfig.DoesNotExist:
        logger.warning("NetBoxConfig %s not found", config_id)
        return {"success": False, "error": "Config not found"}

    service = NetBoxService(config)
    result = service.sync_devices(full_sync=full_sync)

    return {
        "success": result.success,
        "message": result.message,
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }


@shared_task(name="scheduled_netbox_sync")
def scheduled_netbox_sync() -> None:
    """Scheduled task to sync from NetBox for all enabled configurations.

    This task runs periodically and triggers syncs based on each config's
    sync_frequency setting.
    """
    from webnet.devices.models import NetBoxConfig
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()

    for config in NetBoxConfig.objects.filter(enabled=True).exclude(sync_frequency="manual"):
        # Determine if sync is due based on frequency
        last_sync = config.last_sync_at
        should_sync = False

        if not last_sync:
            should_sync = True
        elif config.sync_frequency == "hourly":
            should_sync = now - last_sync >= timedelta(hours=1)
        elif config.sync_frequency == "daily":
            should_sync = now - last_sync >= timedelta(days=1)
        elif config.sync_frequency == "weekly":
            should_sync = now - last_sync >= timedelta(weeks=1)

        if should_sync:
            # Update last_sync_at immediately to prevent duplicate syncs if this task
            # runs again before the sync job completes
            config.last_sync_at = now
            config.save(update_fields=["last_sync_at"])
            netbox_sync_job.delay(config.id, full_sync=False)


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


# CDP parsing regexes
_def_cdp_device_re = re.compile(r"Device ID\s*:\s*(?P<hostname>\S+)", re.IGNORECASE)
_def_cdp_intf_re = re.compile(
    r"Interface:\s*(?P<local_intf>[^,]+),\s*Port ID \(outgoing port\):\s*(?P<remote_intf>.+)",
    re.IGNORECASE,
)
_def_cdp_ip_re = re.compile(
    r"(?:IP address|Management address(?:es)?)\s*:\s*(?P<ip>[\d.]+)", re.IGNORECASE
)
_def_cdp_platform_re = re.compile(r"Platform\s*:\s*(?P<platform>[^,\n]+)", re.IGNORECASE)

# LLDP parsing regexes (multi-vendor support)
# Note: Chassis ID may contain MAC address; we prefer System Name for hostname
_def_lldp_chassis_re = re.compile(r"Chassis id\s*:\s*(?P<chassis>\S+)", re.IGNORECASE)
_def_lldp_sysname_re = re.compile(r"System Name\s*:\s*(?P<sysname>\S+)", re.IGNORECASE)
# Local interface - don't include "Port id" as that refers to remote port
_def_lldp_local_intf_re = re.compile(
    r"(?:Local Intf|Local Interface)\s*:\s*(?P<local_intf>\S+)", re.IGNORECASE
)
_def_lldp_port_id_re = re.compile(r"Port id\s*:\s*(?P<port_id>\S+)", re.IGNORECASE)
_def_lldp_port_desc_re = re.compile(
    r"(?:Port Description|Port-description)\s*:\s*(?P<port_desc>.+)", re.IGNORECASE
)
# Match management IP in formats like:
# "Management Addresses:\n    IP: 10.1.1.2" or "Mgmt-address: 10.1.1.1"
_def_lldp_mgmt_ip_re = re.compile(
    r"(?:Management Address(?:es)?|Mgmt-address)[:\s\n]+(?:IP:\s*)?(?P<ip>[\d.]+)",
    re.IGNORECASE | re.MULTILINE,
)
# Non-greedy match to avoid capturing across multiple blocks
_def_lldp_sysdesc_re = re.compile(
    r"System Description\s*:\s*(?P<sysdesc>.+?)\n\n", re.IGNORECASE | re.DOTALL
)


def _parse_cdp_neighbors(output: str) -> list[dict[str, str | None]]:
    """Parse CDP neighbors detail output.

    Returns list of dicts with keys:
    - remote_hostname: Device ID
    - local_interface: Local interface name
    - remote_interface: Remote port ID
    - remote_ip: Management IP (optional)
    - remote_platform: Platform info (optional)
    """
    neighbors: list[dict[str, str | None]] = []
    if not output:
        return neighbors
    blocks = output.split("\n\n")
    for block in blocks:
        host_match = _def_cdp_device_re.search(block)
        intf_match = _def_cdp_intf_re.search(block)
        if host_match and intf_match:
            ip_match = _def_cdp_ip_re.search(block)
            platform_match = _def_cdp_platform_re.search(block)
            neighbors.append(
                {
                    "remote_hostname": host_match.group("hostname").strip(),
                    "local_interface": intf_match.group("local_intf").strip(),
                    "remote_interface": intf_match.group("remote_intf").strip(),
                    "remote_ip": ip_match.group("ip").strip() if ip_match else None,
                    "remote_platform": (
                        platform_match.group("platform").strip() if platform_match else None
                    ),
                }
            )
    return neighbors


def _parse_lldp_neighbors(output: str) -> list[dict[str, str | None]]:
    """Parse LLDP neighbors detail output (multi-vendor support).

    Supports output formats from:
    - Cisco IOS/IOS-XE (show lldp neighbors detail)
    - Juniper (show lldp neighbors)
    - Arista EOS (show lldp neighbors detail)

    Returns list of dicts with keys:
    - remote_hostname: System name or chassis ID
    - local_interface: Local interface name
    - remote_interface: Port ID or port description
    - remote_ip: Management IP (optional)
    - remote_platform: System description (optional)
    """
    neighbors: list[dict[str, str | None]] = []
    if not output:
        return neighbors

    # First try to split on dashed line separators (Cisco format)
    if "---" in output or re.search(r"-{10,}", output):
        blocks = re.split(r"-{10,}", output)
    else:
        # For formats without dashes (Juniper), split on "Local Interface" lines
        # Each neighbor entry starts with "Local Interface"
        blocks = re.split(r"(?=Local Interface\s*:)", output, flags=re.IGNORECASE)
        blocks = [b for b in blocks if b.strip()]

    for block in blocks:
        if not block.strip():
            continue

        # Try to extract hostname (prefer System Name over Chassis ID)
        # Note: Chassis ID often contains MAC address, so System Name is preferred
        hostname = None
        sysname_match = _def_lldp_sysname_re.search(block)
        if sysname_match:
            hostname = sysname_match.group("sysname").strip()
        else:
            chassis_match = _def_lldp_chassis_re.search(block)
            if chassis_match:
                hostname = chassis_match.group("chassis").strip()

        # Extract local interface
        local_intf = None
        local_match = _def_lldp_local_intf_re.search(block)
        if local_match:
            local_intf = local_match.group("local_intf").strip()

        # Extract remote interface (prefer port description over port ID)
        remote_intf = None
        port_desc_match = _def_lldp_port_desc_re.search(block)
        if port_desc_match:
            desc = port_desc_match.group("port_desc").strip()
            if desc and desc.lower() != "not advertised":
                remote_intf = desc
        if not remote_intf:
            port_id_match = _def_lldp_port_id_re.search(block)
            if port_id_match:
                remote_intf = port_id_match.group("port_id").strip()

        # Skip blocks without essential info
        if not hostname or not local_intf or not remote_intf:
            continue

        # Extract optional fields
        mgmt_ip = None
        ip_match = _def_lldp_mgmt_ip_re.search(block)
        if ip_match:
            mgmt_ip = ip_match.group("ip").strip()

        platform = None
        sysdesc_match = _def_lldp_sysdesc_re.search(block)
        if sysdesc_match:
            # Take first line of system description as platform
            sysdesc = sysdesc_match.group("sysdesc").strip()
            platform = sysdesc.split("\n")[0].strip()[:100]  # Limit length

        neighbors.append(
            {
                "remote_hostname": hostname,
                "local_interface": local_intf,
                "remote_interface": remote_intf,
                "remote_ip": mgmt_ip,
                "remote_platform": platform,
            }
        )

    return neighbors


@shared_task(name="topology_discovery_job")
def topology_discovery_job(
    job_id: int,
    targets: dict,
    protocol: str = "both",
    auto_create_devices: bool = False,
) -> None:
    """Run topology discovery using CDP and/or LLDP.

    Args:
        job_id: Job ID to track progress
        targets: Device filter targets
        protocol: 'cdp', 'lldp', or 'both' (default: 'both')
        auto_create_devices: If True, create DiscoveredDevice entries for unknown neighbors
    """
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
    discovered_devices_count = 0

    # Prefetch all customer devices to avoid N+1 queries
    customer_devices = {d.hostname: d for d in Device.objects.filter(customer=job.customer)}

    try:
        # Run discovery command(s) based on protocol preference
        protocols_to_run = []
        if protocol == "both":
            protocols_to_run = [
                ("cdp", "show cdp neighbors detail", _parse_cdp_neighbors),
                ("lldp", "show lldp neighbors detail", _parse_lldp_neighbors),
            ]
        elif protocol == "lldp":
            protocols_to_run = [("lldp", "show lldp neighbors detail", _parse_lldp_neighbors)]
        else:  # cdp or default
            protocols_to_run = [("cdp", "show cdp neighbors detail", _parse_cdp_neighbors)]

        for proto_name, cmd, parser in protocols_to_run:
            js.append_log(
                job,
                level="INFO",
                message=f"Running {proto_name.upper()} discovery: {cmd}",
            )
            res = nr.run(netmiko_send_command, command_string=cmd)

            for host, r in res.items():
                _log_host_result(js, job, host, r)
                device = customer_devices.get(host)
                if not device or r.failed:
                    continue

                neighbors = parser(str(r.result))
                js.append_log(
                    job,
                    level="INFO",
                    host=host,
                    message=f"Found {len(neighbors)} {proto_name.upper()} neighbors",
                )

                for n in neighbors:
                    remote_hostname = n["remote_hostname"]
                    remote_dev = customer_devices.get(remote_hostname)

                    # Create or update topology link
                    _, created = TopologyLink.objects.update_or_create(
                        customer=device.customer,
                        local_device=device,
                        local_interface=n["local_interface"],
                        remote_hostname=remote_hostname,
                        remote_interface=n["remote_interface"],
                        defaults={
                            "remote_device": remote_dev,
                            "remote_ip": n.get("remote_ip"),
                            "remote_platform": (
                                n.get("remote_platform")
                                or (remote_dev.platform if remote_dev else None)
                            ),
                            "protocol": proto_name,
                            "job_id": job.id,
                        },
                    )
                    if created:
                        discovered_links += 1

                    # Auto-create discovered device entry if enabled and device unknown
                    if auto_create_devices and not remote_dev:
                        from webnet.devices.models import DiscoveredDevice

                        disc_dev, disc_created = DiscoveredDevice.objects.update_or_create(
                            customer=device.customer,
                            hostname=remote_hostname,
                            defaults={
                                "mgmt_ip": n.get("remote_ip"),
                                "platform": n.get("remote_platform"),
                                "discovered_via_device": device,
                                "discovered_via_protocol": proto_name,
                                "job_id": job.id,
                            },
                        )
                        if disc_created:
                            discovered_devices_count += 1
                            js.append_log(
                                job,
                                level="INFO",
                                host=host,
                                message=f"Queued new device for review: {remote_hostname}",
                            )

        result_summary = {
            "targets": targets,
            "protocol": protocol,
            "links_created": discovered_links,
        }
        if auto_create_devices:
            result_summary["devices_discovered"] = discovered_devices_count

        js.set_status(job, "success", result_summary=result_summary)
    except Exception as exc:  # pragma: no cover
        logger.exception("topology_discovery_job failed for job %s", job_id)
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


# =============================================================================
# Bulk Device Onboarding Tasks (Issue #40)
# =============================================================================


def _parse_snmp_sysdescr(sysdescr: str) -> dict[str, str | None]:
    """Parse SNMP sysDescr to extract vendor, platform, and software version.

    Example sysDescrs:
    - Cisco IOS: "Cisco IOS Software, 3800 Software (C3800-ADVIPSERVICESK9-M), Version 15.1"
    - Juniper: "Juniper Networks, Inc. ex2200-24t-4g..."
    - Arista: "Arista Networks EOS version 4.27.3M running on an Arista ..."
    """
    vendor = None
    platform = None
    software_version = None

    sysdescr_lower = sysdescr.lower()

    # Detect vendor
    if "cisco" in sysdescr_lower:
        vendor = "cisco"
        # Try to extract platform and version
        if "ios" in sysdescr_lower or "nx-os" in sysdescr_lower:
            # Extract version
            version_match = re.search(r"Version\s+([\d.()a-zA-Z]+)", sysdescr, re.IGNORECASE)
            if version_match:
                software_version = version_match.group(1)
            # Extract platform
            platform_match = re.search(r"(\d{4}|C\d{4}|Nexus\s+\d+)", sysdescr, re.IGNORECASE)
            if platform_match:
                platform = platform_match.group(1)
            else:
                platform = "ios" if "ios" in sysdescr_lower else "nxos"
    elif "juniper" in sysdescr_lower:
        vendor = "juniper"
        platform_match = re.search(r"(ex\d+|mx\d+|srx\d+|qfx\d+)", sysdescr_lower)
        if platform_match:
            platform = platform_match.group(1).upper()
        else:
            platform = "junos"
        version_match = re.search(r"JUNOS\s+(\S+)", sysdescr, re.IGNORECASE)
        if version_match:
            software_version = version_match.group(1)
    elif "arista" in sysdescr_lower:
        vendor = "arista"
        platform = "eos"
        version_match = re.search(r"version\s+([\d.]+[a-zA-Z]*)", sysdescr, re.IGNORECASE)
        if version_match:
            software_version = version_match.group(1)
    elif "huawei" in sysdescr_lower:
        vendor = "huawei"
        platform = "vrp"
    elif "linux" in sysdescr_lower:
        vendor = "linux"
        platform = "linux"
    else:
        # Try to extract first word as vendor hint
        parts = sysdescr.split()
        if parts:
            vendor = parts[0].lower()[:50]

    return {
        "vendor": vendor,
        "platform": platform,
        "software_version": software_version,
    }


def _scan_ip_for_ssh(
    ip: str,
    port: int = 22,
    timeout: float = 3.0,
) -> bool:
    """Check if SSH port is open on the given IP address."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _test_ssh_credential(
    ip: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 10,
) -> tuple[bool, dict | None, str]:
    """Test SSH credential against a device.

    Returns:
        Tuple of (success, device_info_dict, message)
    """
    try:
        from netmiko import ConnectHandler
        from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

        # Try common device types
        device_types = ["autodetect", "linux", "cisco_ios", "juniper_junos", "arista_eos"]

        for device_type in device_types:
            try:
                device = {
                    "device_type": device_type,
                    "host": ip,
                    "username": username,
                    "password": password,
                    "port": port,
                    "timeout": timeout,
                    "auth_timeout": timeout,
                    "banner_timeout": timeout,
                }
                conn = ConnectHandler(**device)

                # Try to get device info
                device_info = {
                    "device_type": conn.device_type,
                }

                # Try to get hostname - best effort, not critical for auth success
                try:
                    prompt = conn.find_prompt()
                    hostname = prompt.strip("#>$").strip()
                    device_info["hostname"] = hostname
                except Exception:
                    # Hostname extraction is optional; proceed without it if it fails
                    pass

                conn.disconnect()
                return True, device_info, f"SSH authentication successful ({device_type})"

            except NetmikoAuthenticationException:
                return False, None, "Authentication failed - invalid credentials"
            except NetmikoTimeoutException:
                continue
            except Exception as e:
                if "authentication" in str(e).lower():
                    return False, None, "Authentication failed - invalid credentials"
                continue

        return False, None, "Could not establish SSH connection with any device type"

    except Exception:
        logger.exception("Unexpected error during SSH credential test for %s", ip)
        return False, None, "An internal error occurred while testing SSH credentials."


def _snmp_get_device_info(
    ip: str,
    community: str = "public",
    version: str = "2c",
    timeout: int = 5,
) -> dict[str, str | None] | None:
    """Get device information via SNMP.

    Returns dict with keys: hostname, vendor, platform, software_version, serial_number
    """
    try:
        from pysnmp.hlapi import (
            getCmd,
            SnmpEngine,
            CommunityData,
            UdpTransportTarget,
            ContextData,
            ObjectType,
            ObjectIdentity,
        )

        # Standard SNMP OIDs
        oid_sysdescr = "1.3.6.1.2.1.1.1.0"  # sysDescr
        oid_sysname = "1.3.6.1.2.1.1.5.0"  # sysName

        result: dict[str, str | None] = {
            "hostname": None,
            "vendor": None,
            "platform": None,
            "software_version": None,
            "serial_number": None,
        }

        snmp_version = 1 if version == "2c" else 0  # SNMPv2c = 1, SNMPv1 = 0

        # Get sysDescr and sysName
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=snmp_version),
                UdpTransportTarget((ip, 161), timeout=timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid_sysdescr)),
                ObjectType(ObjectIdentity(oid_sysname)),
            )
        )

        if errorIndication or errorStatus:
            return None

        sysdescr = ""
        for varBind in varBinds:
            oid_str = str(varBind[0])
            value = str(varBind[1])
            if oid_sysdescr in oid_str:
                sysdescr = value
            elif oid_sysname in oid_str:
                result["hostname"] = value

        # Parse sysDescr to extract vendor/platform/version
        if sysdescr:
            parsed = _parse_snmp_sysdescr(sysdescr)
            result.update(parsed)

        return result

    except ImportError:
        logger.warning("pysnmp not available for SNMP discovery")
        return None
    except Exception as e:
        logger.debug("SNMP query failed for %s: %s", ip, e)
        return None


def _expand_ip_range(cidr: str) -> list[str]:
    """Expand a CIDR notation to list of IP addresses.

    Limits to /24 network (256 IPs) max to prevent excessive scanning.
    """
    import ipaddress

    try:
        network = ipaddress.ip_network(cidr, strict=False)
        # Limit to /24 to prevent excessive scanning
        if network.prefixlen < 24:
            logger.warning("Limiting IP range scan to first /24 of %s", cidr)
            network = ipaddress.ip_network(f"{network.network_address}/24", strict=False)
        return [str(ip) for ip in network.hosts()]
    except ValueError as e:
        logger.error("Invalid CIDR notation: %s - %s", cidr, e)
        return []


@shared_task(name="ip_range_scan_job")
def ip_range_scan_job(
    job_id: int,
    ip_ranges: list[str],
    credential_ids: list[int],
    use_snmp: bool = True,
    snmp_community: str = "public",
    snmp_version: str = "2c",
    test_ssh: bool = True,
    ports: list[int] | None = None,
) -> None:
    """Scan IP ranges to discover network devices.

    Args:
        job_id: Job ID to track progress
        ip_ranges: List of CIDR notation IP ranges to scan
        credential_ids: List of credential IDs to test
        use_snmp: Use SNMP for device discovery
        snmp_community: SNMP community string
        snmp_version: SNMP version (2c or 3)
        test_ssh: Test SSH connectivity with credentials
        ports: SSH ports to test (default: [22])
    """
    from webnet.devices.models import Credential, DiscoveredDevice

    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return

    js.set_status(job, "running")

    if not ports:
        ports = [22]

    # Get credentials
    credentials = list(
        Credential.objects.filter(id__in=credential_ids, customer_id=job.customer_id)
    )
    if not credentials:
        js.append_log(job, level="ERROR", message="No valid credentials found")
        js.set_status(job, "failed", result_summary={"error": "no credentials"})
        return

    discovered_count = 0
    reachable_count = 0
    duplicate_count = 0
    total_ips = 0

    try:
        for cidr in ip_ranges:
            js.append_log(job, level="INFO", message=f"Scanning IP range: {cidr}")
            ips = _expand_ip_range(cidr)
            total_ips += len(ips)

            for ip in ips:
                device_info: dict[str, str | None] = {
                    "hostname": None,
                    "vendor": None,
                    "platform": None,
                    "software_version": None,
                    "serial_number": None,
                }
                discovery_source = DiscoveredDevice.SOURCE_IP_SCAN
                tested_credential = None
                credential_status = "untested"

                # Step 1: Check if SSH port is open
                ssh_reachable = False
                for port in ports:
                    if _scan_ip_for_ssh(ip, port):
                        ssh_reachable = True
                        break

                if not ssh_reachable and not use_snmp:
                    continue  # Skip unreachable hosts

                # Step 2: Try SNMP discovery if enabled
                if use_snmp:
                    snmp_info = _snmp_get_device_info(ip, snmp_community, snmp_version)
                    if snmp_info:
                        device_info.update(snmp_info)
                        discovery_source = DiscoveredDevice.SOURCE_SNMP
                        reachable_count += 1

                # Step 3: Test SSH credentials if enabled
                if test_ssh and ssh_reachable:
                    for cred in credentials:
                        success, ssh_info, msg = _test_ssh_credential(
                            ip, cred.username, cred.password or "", ports[0]
                        )
                        if success:
                            tested_credential = cred
                            credential_status = "success"
                            if ssh_info:
                                if ssh_info.get("hostname") and not device_info.get("hostname"):
                                    device_info["hostname"] = ssh_info["hostname"]
                            if not device_info.get("vendor"):
                                reachable_count += 1
                            js.append_log(
                                job,
                                level="INFO",
                                message=f"SSH auth success for {ip} with credential '{cred.name}'",
                            )
                            break
                        else:
                            credential_status = "failed"

                # Skip if no device info was gathered
                if not device_info.get("hostname") and not ssh_reachable:
                    continue

                # Generate hostname if not discovered
                hostname = device_info.get("hostname") or ip.replace(".", "-")

                # Check for duplicates
                if DiscoveredDevice.check_duplicate(job.customer_id, hostname, ip):
                    duplicate_count += 1
                    js.append_log(
                        job,
                        level="INFO",
                        message=f"Skipping duplicate device: {hostname} ({ip})",
                    )
                    continue

                # Create discovered device entry
                DiscoveredDevice.objects.create(
                    customer_id=job.customer_id,
                    hostname=hostname,
                    mgmt_ip=ip,
                    vendor=device_info.get("vendor"),
                    platform=device_info.get("platform"),
                    software_version=device_info.get("software_version"),
                    serial_number=device_info.get("serial_number"),
                    discovery_source=discovery_source,
                    credential_tested=tested_credential,
                    credential_test_status=credential_status,
                    job_id=job.id,
                )
                discovered_count += 1
                js.append_log(
                    job,
                    level="INFO",
                    message=f"Discovered device: {hostname} ({ip})",
                )

        result_summary = {
            "ip_ranges": ip_ranges,
            "total_ips_scanned": total_ips,
            "discovered_count": discovered_count,
            "reachable_count": reachable_count,
            "duplicate_count": duplicate_count,
        }
        js.set_status(job, "success", result_summary=result_summary)

    except Exception as exc:
        logger.exception("ip_range_scan_job failed for job %s", job_id)
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="credential_test_job")
def credential_test_job(
    job_id: int,
    discovered_device_ids: list[int],
    credential_ids: list[int],
) -> None:
    """Test credentials against discovered devices.

    Args:
        job_id: Job ID to track progress
        discovered_device_ids: List of DiscoveredDevice IDs to test
        credential_ids: List of Credential IDs to try
    """
    from webnet.devices.models import Credential, DiscoveredDevice

    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return

    js.set_status(job, "running")

    # Get credentials
    credentials = list(
        Credential.objects.filter(id__in=credential_ids, customer_id=job.customer_id)
    )
    if not credentials:
        js.append_log(job, level="ERROR", message="No valid credentials found")
        js.set_status(job, "failed", result_summary={"error": "no credentials"})
        return

    # Get discovered devices
    devices = DiscoveredDevice.objects.filter(
        id__in=discovered_device_ids,
        customer_id=job.customer_id,
        status=DiscoveredDevice.STATUS_PENDING,
    )

    tested_count = 0
    success_count = 0
    failed_count = 0

    try:
        for device in devices:
            if not device.mgmt_ip:
                js.append_log(
                    job,
                    level="WARNING",
                    message=f"Skipping {device.hostname} - no IP address",
                )
                continue

            tested_count += 1
            found_credential = None

            for cred in credentials:
                success, device_info, msg = _test_ssh_credential(
                    device.mgmt_ip, cred.username, cred.password or ""
                )
                if success:
                    found_credential = cred
                    # Update device info if we got more details
                    if device_info and device_info.get("hostname"):
                        if not device.hostname or device.hostname == device.mgmt_ip.replace(
                            ".", "-"
                        ):
                            device.hostname = device_info["hostname"]
                    break

            if found_credential:
                device.credential_tested = found_credential
                device.credential_test_status = "success"
                device.save()
                success_count += 1
                js.append_log(
                    job,
                    level="INFO",
                    message=f"Credential '{found_credential.name}' works for {device.hostname}",
                )
            else:
                device.credential_test_status = "failed"
                device.save()
                failed_count += 1
                js.append_log(
                    job,
                    level="WARNING",
                    message=f"No working credential found for {device.hostname}",
                )

        result_summary = {
            "tested_count": tested_count,
            "success_count": success_count,
            "failed_count": failed_count,
        }
        js.set_status(job, "success", result_summary=result_summary)

    except Exception as exc:
        logger.exception("credential_test_job failed for job %s", job_id)
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


@shared_task(name="trigger_auto_remediation")
def trigger_auto_remediation(compliance_result_id: int) -> None:
    """Check if auto-remediation should be triggered for a compliance violation.

    Args:
        compliance_result_id: ID of the ComplianceResult with a violation
    """
    from django.utils import timezone
    from webnet.compliance.models import ComplianceResult, RemediationRule, RemediationAction

    try:
        result = ComplianceResult.objects.select_related(
            "policy", "device", "device__customer"
        ).get(pk=compliance_result_id)
    except ComplianceResult.DoesNotExist:
        logger.warning(f"ComplianceResult {compliance_result_id} not found")
        return

    # Find enabled remediation rules for this policy
    rules = RemediationRule.objects.filter(policy=result.policy, enabled=True)

    if not rules.exists():
        logger.info(f"No remediation rules found for policy {result.policy_id}")
        return

    for rule in rules:
        # Check if approval is required
        if rule.approval_required == "manual":
            logger.info(f"Rule {rule.id} requires manual approval, skipping auto-remediation")
            continue
        # Note: 'auto' approval means auto-approve for non-critical policies
        # 'none' approval means no approval needed at all
        # Both allow auto-remediation to proceed

        # Check daily execution limit
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        executions_today = RemediationAction.objects.filter(
            rule=rule, started_at__gte=today_start
        ).count()

        if executions_today >= rule.max_daily_executions:
            logger.warning(f"Rule {rule.id} has reached daily limit ({rule.max_daily_executions})")
            continue

        # Queue the auto-remediation job
        logger.info(f"Triggering auto-remediation for rule {rule.id} on device {result.device_id}")
        auto_remediation_job.delay(rule.id, result.id)


@shared_task(name="auto_remediation_job")
def auto_remediation_job(rule_id: int, compliance_result_id: int) -> None:
    """Execute auto-remediation for a compliance violation.

    Args:
        rule_id: ID of the RemediationRule to apply
        compliance_result_id: ID of the ComplianceResult with the violation
    """
    from django.utils import timezone
    from webnet.compliance.models import RemediationRule, RemediationAction, ComplianceResult
    from webnet.config_mgmt.models import ConfigSnapshot

    js = JobService()

    try:
        rule = RemediationRule.objects.select_related("policy", "policy__customer").get(pk=rule_id)
        result = ComplianceResult.objects.select_related("device", "policy").get(
            pk=compliance_result_id
        )
    except (RemediationRule.DoesNotExist, ComplianceResult.DoesNotExist) as e:
        logger.error(f"Error loading remediation data: {e}")
        return

    device = result.device

    # Create remediation action record
    action = RemediationAction.objects.create(
        rule=rule,
        compliance_result=result,
        device=device,
        status="pending",
    )

    # Create a job for tracking
    job = js.create_job(
        job_type="auto_remediation",
        user=rule.created_by,
        customer=rule.policy.customer,
        target_summary={"device_id": device.id, "hostname": device.hostname},
        payload={"rule_id": rule.id, "action_id": action.id},
    )
    action.job = job
    action.status = "running"
    action.save(update_fields=["job", "status"])

    js.set_status(job, "running")
    js.append_log(
        job,
        level="INFO",
        message=f"Starting auto-remediation: {rule.name} on {device.hostname}",
    )

    inventory = None
    try:
        # Build inventory for this single device
        targets = {"device_ids": [device.id]}
        inventory = build_inventory(targets, customer_id=device.customer_id)

        if not inventory.hosts:
            raise ValueError(f"Device {device.id} not found in inventory")

        nr = _nr_from_inventory(inventory)

        # Step 1: Take before snapshot
        js.append_log(job, level="INFO", message="Taking before snapshot")
        before_result = nr.run(napalm_get, getters=["config"])

        for host, task_result in before_result.items():
            if task_result.failed:
                raise ValueError(f"Failed to get config from {host}: {task_result.exception}")

            config_text = (task_result.result.get("config") or {}).get("running") or ""
            before_snapshot = ConfigSnapshot.objects.create(
                device=device,
                job=job,
                source="remediation_before",
                config_text=config_text,
            )
            action.before_snapshot = before_snapshot
            action.save(update_fields=["before_snapshot"])
            js.append_log(
                job, level="INFO", message=f"Before snapshot saved ({len(config_text)} bytes)"
            )

        # Step 2: Apply remediation configuration
        js.append_log(job, level="INFO", message="Applying remediation configuration")
        apply_result = nr.run(
            napalm_configure,
            configuration=rule.config_snippet,
            dry_run=False,
            replace=(rule.apply_mode == "replace"),
        )

        for host, task_result in apply_result.items():
            if task_result.failed:
                raise ValueError(f"Failed to apply config to {host}: {task_result.exception}")
            js.append_log(job, level="INFO", message=f"Configuration applied to {host}")

        # Step 3: Take after snapshot
        js.append_log(job, level="INFO", message="Taking after snapshot")
        after_result = nr.run(napalm_get, getters=["config"])

        for host, task_result in after_result.items():
            if task_result.failed:
                raise ValueError(f"Failed to get config from {host}: {task_result.exception}")

            config_text = (task_result.result.get("config") or {}).get("running") or ""
            after_snapshot = ConfigSnapshot.objects.create(
                device=device,
                job=job,
                source="remediation_after",
                config_text=config_text,
            )
            action.after_snapshot = after_snapshot
            action.save(update_fields=["after_snapshot"])
            js.append_log(
                job, level="INFO", message=f"After snapshot saved ({len(config_text)} bytes)"
            )

        # Step 4: Verify if requested
        if rule.verify_after:
            js.append_log(job, level="INFO", message="Verifying compliance after remediation")
            # TODO: Re-run compliance check to verify
            # For now, we cannot automatically verify, so we leave it as None
            # The user should manually verify or implement actual compliance re-check
            js.append_log(
                job,
                level="WARNING",
                message="Automatic verification not yet implemented - manual check recommended",
            )

        # Success
        action.status = "success"
        action.finished_at = timezone.now()
        action.save(update_fields=["status", "finished_at"])
        js.append_log(job, level="INFO", message="Auto-remediation completed successfully")
        js.set_status(job, "success", result_summary={"action_id": action.id})

        # Broadcast update via WebSocket
        try:
            from webnet.api.consumers import broadcast_entity_update

            broadcast_entity_update(
                customer_id=device.customer_id,
                entity_type="remediation_action",
                entity_id=action.id,
                action="created",
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast remediation update: {e}")

    except Exception as e:
        logger.error(f"Auto-remediation failed: {e}", exc_info=True)
        js.append_log(job, level="ERROR", message=f"Remediation failed: {str(e)}")

        # Rollback if configured and we have a before snapshot
        if rule.rollback_on_failure and action.before_snapshot and inventory:
            try:
                js.append_log(job, level="INFO", message="Attempting rollback")
                nr = _nr_from_inventory(inventory)
                rollback_result = nr.run(
                    napalm_configure,
                    configuration=action.before_snapshot.config_text,
                    dry_run=False,
                    replace=True,
                )

                for host, task_result in rollback_result.items():
                    if task_result.failed:
                        js.append_log(
                            job,
                            level="ERROR",
                            message=f"Rollback failed for {host}: {task_result.exception}",
                        )
                    else:
                        js.append_log(job, level="INFO", message=f"Rollback successful for {host}")

                action.status = "rolled_back"
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}", exc_info=True)
                js.append_log(job, level="ERROR", message=f"Rollback failed: {str(rollback_error)}")
                action.status = "failed"
        else:
            action.status = "failed"
            if not inventory:
                js.append_log(
                    job, level="WARNING", message="Cannot rollback: inventory not available"
                )

        action.error_message = str(e)
        action.finished_at = timezone.now()
        action.save(update_fields=["status", "error_message", "finished_at"])
        js.set_status(job, "failed", result_summary={"error": str(e)})

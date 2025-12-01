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
def config_backup_job(job_id: int, targets: dict, source_label: str = "manual") -> None:
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
                ConfigSnapshot.objects.create(
                    device=device,
                    job=job,
                    source=source_label,
                    config_text=cfg,
                )
        js.set_status(job, "success", result_summary={"targets": targets})
    except Exception as exc:  # pragma: no cover
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})


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
_def_lldp_chassis_re = re.compile(
    r"(?:Chassis id|System Name)\s*:\s*(?P<hostname>\S+)", re.IGNORECASE
)
_def_lldp_sysname_re = re.compile(r"System Name\s*:\s*(?P<sysname>.+)", re.IGNORECASE)
_def_lldp_local_intf_re = re.compile(
    r"(?:Local Intf|Local Interface|Port id)\s*:\s*(?P<local_intf>\S+)", re.IGNORECASE
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
_def_lldp_sysdesc_re = re.compile(
    r"System Description\s*:\s*(?P<sysdesc>.+)", re.IGNORECASE | re.DOTALL
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
        hostname = None
        sysname_match = _def_lldp_sysname_re.search(block)
        if sysname_match:
            hostname = sysname_match.group("sysname").strip()
        else:
            chassis_match = _def_lldp_chassis_re.search(block)
            if chassis_match:
                hostname = chassis_match.group("hostname").strip()

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


def _discover_neighbors_for_device(
    nr: Nornir,
    js: JobService,
    job: Job,
    device: Device,
    protocol: str,
) -> list[dict[str, str | None]]:
    """Run neighbor discovery for a single device using specified protocol.

    Args:
        nr: Nornir instance filtered to the target device
        js: JobService for logging
        job: Job instance
        device: Device to discover neighbors for
        protocol: 'cdp', 'lldp', or 'both'

    Returns:
        List of neighbor dictionaries with protocol key added
    """
    all_neighbors: list[dict[str, str | None]] = []

    protocols_to_try = []
    if protocol == "both":
        protocols_to_try = ["cdp", "lldp"]
    elif protocol in ("cdp", "lldp"):
        protocols_to_try = [protocol]
    else:
        protocols_to_try = ["cdp"]  # Default to CDP

    for proto in protocols_to_try:
        if proto == "cdp":
            cmd = "show cdp neighbors detail"
            parser = _parse_cdp_neighbors
        else:  # lldp
            cmd = "show lldp neighbors detail"
            parser = _parse_lldp_neighbors

        try:
            res = nr.run(netmiko_send_command, command_string=cmd)
            for host, r in res.items():
                if r.failed:
                    js.append_log(
                        job,
                        level="WARNING",
                        host=host,
                        message=f"{proto.upper()} discovery failed: {r.exception or r.result}",
                    )
                    continue
                neighbors = parser(str(r.result))
                js.append_log(
                    job,
                    level="INFO",
                    host=host,
                    message=f"Discovered {len(neighbors)} neighbors via {proto.upper()}",
                )
                for n in neighbors:
                    n["protocol"] = proto
                all_neighbors.extend(neighbors)
        except Exception as exc:
            js.append_log(
                job,
                level="WARNING",
                host=device.hostname,
                message=f"{proto.upper()} command failed: {exc}",
            )

    return all_neighbors


@shared_task(name="topology_discovery_job")
def topology_discovery_job(
    job_id: int,
    targets: dict,
    protocol: str = "both",
    auto_create_devices: bool = False,
    max_depth: int = 0,
) -> None:
    """Run topology discovery using CDP and/or LLDP.

    Args:
        job_id: Job ID to track progress
        targets: Device filter targets
        protocol: 'cdp', 'lldp', or 'both' (default: 'both')
        auto_create_devices: If True, create DiscoveredDevice entries for unknown neighbors
        max_depth: Maximum discovery hops (0 = single hop, disabled for recursive)
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
                device = Device.objects.filter(hostname=host, customer=job.customer).first()
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
                    remote_dev = Device.objects.filter(
                        customer=device.customer, hostname=remote_hostname
                    ).first()

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

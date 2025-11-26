"""Ad-hoc network tasks for devices provided via request payload.

These tasks create a temporary Nornir inventory from device credentials
passed directly in the request, rather than using the database-backed inventory.
This enables executing commands on devices without requiring them to be registered.
"""

import os
import socket
import tempfile
import traceback
from typing import Any

import yaml
from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.task import Task
from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class AdHocDevice(BaseModel):
    """Device credentials for ad-hoc operations."""

    hostname: str
    ip: str
    platform: str
    username: str
    password: str
    port: int = 22


class CommandRequest(BaseModel):
    """Request payload for running commands."""

    devices: list[AdHocDevice]
    commands: list[str]


class ComplianceRequest(BaseModel):
    """Request payload for NAPALM getters."""

    devices: list[AdHocDevice]
    getters: list[str]


class ReachabilityRequest(BaseModel):
    """Request payload for reachability check."""

    devices: list[AdHocDevice]


def adapt_platform(platform: str) -> str:
    """Map platform names to Netmiko device types."""
    pmap = {
        "ios": "cisco_ios",
        "nxos": "cisco_nxos",
        "eos": "arista_eos",
        "junos": "juniper_junos",
        "iosxr": "cisco_xr",
        "linux": "linux",
    }
    return pmap.get(platform, platform)


def get_ssh_config_path() -> str:
    """Get the path to the SSH config file."""
    # Check if running in container (/app/ssh_config) or local dev
    container_path = "/app/ssh_config"
    if os.path.exists(container_path):
        return container_path
    # Fall back to local path relative to this file
    local_path = os.path.join(os.path.dirname(__file__), "..", "..", "ssh_config")
    if os.path.exists(local_path):
        return local_path
    return container_path  # Default to container path


def create_adhoc_nornir(devices: list[AdHocDevice]) -> Nornir:
    """Create a Nornir instance with temporary inventory from device list."""
    ssh_config = get_ssh_config_path()

    hosts = {
        d.hostname: {
            "hostname": d.ip,
            "port": d.port,
            "username": d.username,
            "password": d.password,
            "platform": adapt_platform(d.platform),
            "connection_options": {
                "netmiko": {
                    "extras": {
                        "use_keys": False,
                        "key_file": None,
                        "ssh_config_file": ssh_config,
                        "global_delay_factor": 2,
                    }
                }
            },
        }
        for d in devices
    }

    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml")
    yaml.dump(hosts, tf)
    tf.close()

    nr = InitNornir(
        inventory={
            "plugin": "SimpleInventory",
            "options": {"host_file": tf.name},
        },
        dry_run=False,
        logging={"enabled": False},
    )

    try:
        os.unlink(tf.name)
    except OSError:
        pass

    return nr


def adhoc_run_commands_task(task: Task, commands: list[str]) -> dict[str, str]:
    """Run multiple commands on a device using Netmiko."""
    results: dict[str, str] = {}
    for cmd in commands:
        try:
            res = task.run(task=netmiko_send_command, command_string=cmd)
            results[cmd] = res.result
        except Exception as e:
            results[cmd] = f"ERROR: {str(e)}"
    return results


def adhoc_check_reachability_task(task: Task) -> str:
    """Check if a device is reachable via TCP connection to its SSH port."""
    target = task.host.hostname
    port = task.host.port or 22
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((target, port))
        sock.close()
        if result == 0:
            return "reachable"
        return "unreachable"
    except Exception:
        return "unreachable"


def execute_adhoc_commands(request: CommandRequest) -> dict[str, Any]:
    """Execute commands on ad-hoc devices and return results."""
    try:
        nr = create_adhoc_nornir(request.devices)
        result = nr.run(task=adhoc_run_commands_task, commands=request.commands)

        output: dict[str, Any] = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                logger.error("Task failed for %s", hostname)

                err_msg = "Unknown error"
                if host_res.result and isinstance(host_res.result, str):
                    err_msg = host_res.result
                elif host_res.exception:
                    err_msg = str(host_res.exception)

                logger.error("Underlying error: %s", err_msg)
                if host_res.exception:
                    traceback.print_exception(
                        type(host_res.exception),
                        host_res.exception,
                        host_res.exception.__traceback__,
                    )

                output[hostname] = {"status": "failed", "error": err_msg}
            else:
                task_result = host_res[0].result
                output[hostname] = {"status": "success", "result": task_result}

        return output
    except Exception as e:
        logger.exception("Error executing ad-hoc commands")
        return {"error": str(e), "status": "failed"}


def execute_adhoc_getters(request: ComplianceRequest) -> dict[str, Any]:
    """Execute NAPALM getters on ad-hoc devices and return results."""
    try:
        nr = create_adhoc_nornir(request.devices)
        result = nr.run(task=napalm_get, getters=request.getters)

        output: dict[str, Any] = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                logger.error("Task failed for %s", hostname)

                err_msg = "Unknown error"
                if host_res.result and isinstance(host_res.result, str):
                    err_msg = host_res.result
                elif host_res.exception:
                    err_msg = str(host_res.exception)

                logger.error("Underlying error: %s", err_msg)
                if host_res.exception:
                    traceback.print_exception(
                        type(host_res.exception),
                        host_res.exception,
                        host_res.exception.__traceback__,
                    )

                output[hostname] = {"status": "failed", "error": err_msg}
            else:
                output[hostname] = {"status": "success", "result": host_res[0].result}

        return output
    except Exception as e:
        logger.exception("Error executing ad-hoc getters")
        return {"error": str(e), "status": "failed"}


def execute_adhoc_reachability(request: ReachabilityRequest) -> dict[str, Any]:
    """Check reachability on ad-hoc devices and return results."""
    try:
        # Create a CommandRequest wrapper since create_adhoc_nornir expects it
        nr = create_adhoc_nornir(request.devices)
        result = nr.run(task=adhoc_check_reachability_task)

        output: dict[str, Any] = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                output[hostname] = {
                    "status": "error",
                    "reachability": "unreachable",
                    "error": str(host_res.exception),
                }
            else:
                reachability = host_res[0].result
                output[hostname] = {"status": "success", "reachability": reachability}

        return output
    except Exception as e:
        logger.exception("Error checking ad-hoc reachability")
        return {"error": str(e), "status": "failed"}

from __future__ import annotations

from typing import Any

from netmiko import ConnectHandler
from nornir.core.task import Result, Task

from app.core.config import settings


def _build_connection_params(task: Task, timeout: int | None) -> dict[str, Any]:
    device_type = task.host.data.get("netmiko_device_type") or task.host.platform
    if not device_type:
        raise ValueError("Device missing Netmiko device_type/platform")
    params = {
        "device_type": device_type,
        "host": task.host.hostname,
        "username": task.host.username,
        "password": task.host.password,
        "port": task.host.port,
        "fast_cli": False,
        "timeout": timeout or 60,
    }
    optional_args = task.host.data.get("metadata", {}).get("netmiko_optional_args", {})
    params.update(optional_args)
    return params


def run_commands(task: Task, commands: list[str], timeout: int | None = None) -> Result:
    if settings.dry_run_mode:
        outputs = {command: f"DRY-RUN: {command} on {task.host.name}" for command in commands}
        return Result(host=task.host, result=outputs)

    params = _build_connection_params(task, timeout)
    connection = ConnectHandler(**params)
    try:
        outputs = {}
        for command in commands:
            outputs[command] = connection.send_command(command, read_timeout=timeout or 60)
    finally:
        connection.disconnect()
    return Result(host=task.host, result=outputs)

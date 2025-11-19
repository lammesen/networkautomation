from __future__ import annotations

from nornir.core.task import Result, Task

from app.automation.napalm_device import napalm_device


def get_running_config(task: Task) -> Result:
    """Retrieve the running configuration from a device using NAPALM."""
    with napalm_device(task.host) as device:
        running = device.get_config().get("running", "")
    return Result(host=task.host, result=running)


def preview_merge(task: Task, snippet: str, mode: str = "merge") -> Result:
    """Preview configuration changes before applying them to a device."""
    with napalm_device(task.host) as device:
        device.load_merge_candidate(config=snippet)
        diff = device.compare_config()
        device.discard_config()
    return Result(host=task.host, result=diff)


def commit_merge(task: Task, snippet: str, mode: str = "merge") -> Result:
    """Apply and commit configuration changes to a device."""
    with napalm_device(task.host) as device:
        device.load_merge_candidate(config=snippet)
        diff = device.compare_config()
        if not diff:
            device.discard_config()
            return Result(host=task.host, result="No changes detected", failed=False)
        device.commit_config()
    return Result(host=task.host, result={"diff": diff, "mode": mode})

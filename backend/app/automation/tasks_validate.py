from __future__ import annotations

from nornir.core.task import Result, Task

from app.automation.napalm_device import napalm_device


def run_policy(task: Task, policy: dict) -> Result:
    """Run a compliance policy check against a device."""
    with napalm_device(task.host) as device:
        report = device.compliance_report(policy)
        status = "pass" if report.get("complies") else "fail"
        payload = {"status": status, "details": report}
    return Result(host=task.host, result=payload, failed=status != "pass")

"""Compliance validation tasks using NAPALM."""

import yaml
from nornir.core.task import Result, Task
from nornir_napalm.plugins.tasks import napalm_validate


def validate_task(task: Task, validation_source: str) -> Result:
    """Validate device state using NAPALM's validate mechanism."""
    # Ensure YAML is well-formed before sending to devices
    parsed = yaml.safe_load(validation_source) or {}

    result = task.run(
        task=napalm_validate,
        src=parsed,
        name="Compliance validation",
    )

    return Result(
        host=task.host,
        result=result.result,
        failed=result.failed,
        exception=result.exception,
    )

from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import napalm_validate


def run_validation(task: Task, validation_source: str) -> Result:
    """
    Runs a NAPALM validation against a device.
    """
    result = task.run(task=napalm_validate, src=validation_source)
    return Result(host=task.host, result=result)

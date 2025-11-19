from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import napalm_cli


def run_commands(task: Task, commands: list) -> Result:
    """
    Runs a list of CLI commands on a device.
    """
    result = task.run(task=napalm_cli, commands=commands)
    return Result(host=task.host, result=result)

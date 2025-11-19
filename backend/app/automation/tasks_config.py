from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import (
    napalm_get,
    napalm_configure,
    napalm_compare_config,
    napalm_commit,
    napalm_rollback,
)


def get_config(task: Task) -> Result:
    """
    Gets the running configuration from a device.
    """
    result = task.run(task=napalm_get, getters=["config"], retrieve="running")
    return Result(host=task.host, result=result[0].result["config"]["running"])


def load_merge_candidate(task: Task, config: str) -> Result:
    """
    Loads a merge candidate configuration onto a device.
    """
    result = task.run(task=napalm_configure, configuration=config, replace=False)
    return Result(host=task.host, result=result)


def compare_config(task: Task) -> Result:
    """
    Compares the candidate configuration with the running configuration.
    """
    result = task.run(task=napalm_compare_config)
    return Result(host=task.host, result=result[0].diff)


def commit_config(task: Task) -> Result:
    """
    Commits the candidate configuration.
    """
    result = task.run(task=napalm_commit)
    return Result(host=task.host, result=result)


def rollback_config(task: Task) -> Result:
    """
    Rolls back the configuration.
    """
    result = task.run(task=napalm_rollback)
    return Result(host=task.host, result=result)

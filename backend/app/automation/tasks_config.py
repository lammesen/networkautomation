"""Configuration management tasks using NAPALM."""

from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import (
    napalm_get,
    napalm_configure,
)


def get_config_task(task: Task, retrieve: str = "running") -> Result:
    """Get device configuration using NAPALM."""
    result = task.run(
        task=napalm_get,
        getters=["config"],
        retrieve=retrieve,
        name="Get configuration",
    )
    
    config_text = result.result.get("config", {}).get(retrieve, "")
    
    return Result(
        host=task.host,
        result=config_text,
    )


def load_merge_config_task(task: Task, config: str, dry_run: bool = True) -> Result:
    """Load merge candidate configuration using NAPALM."""
    result = task.run(
        task=napalm_configure,
        configuration=config,
        replace=False,
        dry_run=dry_run,
        name="Load merge configuration",
    )
    
    return Result(
        host=task.host,
        result=result.result,
        diff=result.diff,
    )


def load_replace_config_task(task: Task, config: str, dry_run: bool = True) -> Result:
    """Load replace candidate configuration using NAPALM."""
    result = task.run(
        task=napalm_configure,
        configuration=config,
        replace=True,
        dry_run=dry_run,
        name="Load replace configuration",
    )
    
    return Result(
        host=task.host,
        result=result.result,
        diff=result.diff,
    )


def commit_config_task(task: Task) -> Result:
    """Commit configuration changes using NAPALM."""
    # This is handled by napalm_configure with dry_run=False
    return Result(
        host=task.host,
        result="Committed",
    )

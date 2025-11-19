"""Automation module initialization."""

from .inventory import get_nornir_inventory, filter_devices_from_db
from .nornir_init import init_nornir, filter_nornir_hosts
from .tasks_cli import run_commands_task
from .tasks_config import (
    get_config_task,
    load_merge_config_task,
    load_replace_config_task,
    commit_config_task,
)
from .tasks_validate import validate_task

__all__ = [
    "get_nornir_inventory",
    "filter_devices_from_db",
    "init_nornir",
    "filter_nornir_hosts",
    "run_commands_task",
    "get_config_task",
    "load_merge_config_task",
    "load_replace_config_task",
    "commit_config_task",
    "validate_task",
]

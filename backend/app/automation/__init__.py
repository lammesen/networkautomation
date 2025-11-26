"""Automation module initialization."""

from .context import AutomationContext
from .inventory import filter_devices_from_db, get_nornir_inventory
from .nornir_init import filter_nornir_hosts, init_nornir
from .tasks_cli import run_commands_task
from .tasks_config import (
    commit_config_task,
    get_config_task,
    load_merge_config_task,
    load_replace_config_task,
)
from .tasks_network import (
    AdHocDevice,
    CommandRequest,
    ComplianceRequest,
    ReachabilityRequest,
    create_adhoc_nornir,
    execute_adhoc_commands,
    execute_adhoc_getters,
    execute_adhoc_reachability,
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
    "AutomationContext",
    # Ad-hoc network tasks
    "AdHocDevice",
    "CommandRequest",
    "ComplianceRequest",
    "ReachabilityRequest",
    "create_adhoc_nornir",
    "execute_adhoc_commands",
    "execute_adhoc_getters",
    "execute_adhoc_reachability",
]

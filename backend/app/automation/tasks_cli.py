"""CLI command execution tasks using Netmiko."""

from nornir.core.task import Task, Result
from nornir_netmiko.tasks import netmiko_send_command


def run_commands_task(task: Task, commands: list[str]) -> Result:
    """Run multiple commands on a device using Netmiko."""
    results = {}
    
    for command in commands:
        try:
            result = task.run(
                task=netmiko_send_command,
                command_string=command,
                name=f"Command: {command}",
            )
            results[command] = result.result
        except Exception as e:
            results[command] = f"ERROR: {str(e)}"
    
    return Result(
        host=task.host,
        result=results,
    )

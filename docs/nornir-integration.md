# Nornir Integration Guide

Guide to using Nornir for network automation tasks in the webnet application.

## Table of Contents
- [Overview](#overview)
- [Inventory Building](#inventory-building)
- [Task Execution](#task-execution)
- [Supported Drivers](#supported-drivers)
- [Error Handling](#error-handling)
- [Adding New Tasks](#adding-new-tasks)
- [Best Practices](#best-practices)

## Overview

Nornir is used for parallel network device automation. The application builds Nornir inventory from Django models and executes tasks via Celery workers.

### Architecture

```
Django Models (Device, Credential)
    ↓
build_inventory() → Nornir Inventory
    ↓
Nornir Instance → Task Execution
    ↓
Results → Job Logs & Status
```

## Inventory Building

### Function Signature
```python
from webnet.automation import build_inventory

inventory = build_inventory(
    filters: dict | None = None,
    customer_id: int | None = None
) -> Inventory
```

### Filter Parameters
```python
# Filter by device IDs
inventory = build_inventory(
    filters={"device_ids": [1, 2, 3]},
    customer_id=customer_id
)

# Filter by vendor
inventory = build_inventory(
    filters={"vendor": "cisco"},
    customer_id=customer_id
)

# Filter by site
inventory = build_inventory(
    filters={"site": "datacenter1"},
    customer_id=customer_id
)

# Multiple filters
inventory = build_inventory(
    filters={
        "vendor": "cisco",
        "site": "datacenter1"
    },
    customer_id=customer_id
)
```

### Inventory Structure
Each host in inventory contains:
- `name`: Device hostname
- `hostname`: Management IP address
- `platform`: Device platform (e.g., "ios", "junos")
- `username`: From credential
- `password`: Decrypted password from credential
- `extras`: Metadata (customer_id, device_id, role, site, vendor)
- `connection_options`: Netmiko/NAPALM options

## Task Execution

### Basic Task Pattern
```python
from nornir.core import Nornir
from nornir.core.plugins.runners import ThreadedRunner
from webnet.automation import build_inventory

# Build inventory
inventory = build_inventory(targets, customer_id=job.customer_id)

# Create Nornir instance
nr = Nornir(inventory=inventory, runner=ThreadedRunner())

# Execute task
results = nr.run(task_function, **task_kwargs)

# Process results
for host, result in results.items():
    if result.failed:
        # Handle error
        logger.error(f"{host}: {result.exception}")
    else:
        # Handle success
        logger.info(f"{host}: {result.result}")
```

### Netmiko Tasks (CLI Commands)
```python
from nornir_netmiko.tasks import netmiko_send_command

# Single command
results = nr.run(
    netmiko_send_command,
    command_string="show version",
    timeout=30
)

# Multiple commands
commands = ["show version", "show interfaces"]
for cmd in commands:
    results = nr.run(
        netmiko_send_command,
        command_string=cmd,
        timeout=30
    )
    # Process results
```

### NAPALM Tasks (Configuration)
```python
from nornir_napalm.tasks import napalm_get, napalm_configure

# Get configuration
results = nr.run(
    napalm_get,
    getters=["config"]
)

for host, result in results.items():
    if not result.failed:
        config = result.result.get("config", {}).get("running", "")

# Configure device (preview)
results = nr.run(
    napalm_configure,
    configuration=config_snippet,
    dry_run=True,  # Preview mode
    replace=False  # Merge mode
)

# Configure device (commit)
results = nr.run(
    napalm_configure,
    configuration=config_snippet,
    dry_run=False,  # Commit mode
    replace=True  # Replace entire config
)
```

## Supported Drivers

### Netmiko
For raw CLI command execution:
- Cisco IOS/IOS-XE/IOS-XR
- Juniper Junos
- Arista EOS
- Cisco NX-OS
- And more via Netmiko device types

### NAPALM
For vendor-agnostic operations:
- `napalm_ios`: Cisco IOS/IOS-XE
- `napalm_junos`: Juniper Junos
- `napalm_eos`: Arista EOS
- `napalm_nxos`: Cisco NX-OS
- `napalm_iosxr`: Cisco IOS-XR

### Platform Mapping
Platforms are mapped automatically based on device `vendor` and `platform` fields:

```python
# Example mappings (handled by Nornir)
"cisco" + "ios" → napalm_ios
"juniper" + "junos" → napalm_junos
"arista" + "eos" → napalm_eos
```

## Error Handling

### Result Processing Pattern
```python
def _log_host_result(js: JobService, job: Job, host: str, result) -> None:
    if result.failed:
        js.append_log(
            job,
            level="ERROR",
            host=host,
            message=str(result.exception or result.result)
        )
    else:
        js.append_log(
            job,
            level="INFO",
            host=host,
            message=str(result.result)
        )

# In task
results = nr.run(task_function)
for host, r in results.items():
    _log_host_result(js, job, host, r)
```

### Partial Success Handling
```python
results = nr.run(task_function)
success_count = 0
failure_count = 0

for host, r in results.items():
    if r.failed:
        failure_count += 1
        _log_host_result(js, job, host, r)
    else:
        success_count += 1
        _log_host_result(js, job, host, r)

# Set status based on results
if failure_count == 0:
    js.set_status(job, "success")
elif success_count > 0:
    js.set_status(job, "partial")
else:
    js.set_status(job, "failed")
```

## Adding New Tasks

### Task Template
```python
from celery import shared_task
from webnet.jobs.models import Job
from webnet.jobs.services import JobService
from webnet.automation import build_inventory

@shared_task(name="my_custom_task")
def my_custom_task(job_id: int, targets: dict, **kwargs) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        logger.warning("Job %s not found", job_id)
        return
    
    js.set_status(job, "running")
    
    # Build inventory
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    
    # Create Nornir instance
    from nornir.core import Nornir
    from nornir.core.plugins.runners import ThreadedRunner
    nr = Nornir(inventory=inventory, runner=ThreadedRunner())
    
    try:
        # Execute Nornir task
        results = nr.run(my_nornir_task, **kwargs)
        
        # Process results
        for host, r in results.items():
            _log_host_result(js, job, host, r)
        
        # Set final status
        js.set_status(job, "success", result_summary={"targets": targets})
    except Exception as exc:
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})
```

### Custom Nornir Task
```python
from nornir.core.task import Task, Result

def my_nornir_task(task: Task, param1: str, param2: int) -> Result:
    """Custom Nornir task."""
    host = task.host
    
    try:
        # Task logic here
        result_data = perform_operation(host, param1, param2)
        return Result(
            host=host,
            result=result_data,
            failed=False
        )
    except Exception as e:
        return Result(
            host=host,
            result=None,
            failed=True,
            exception=e
        )

# Use in Celery task
results = nr.run(my_nornir_task, param1="value", param2=42)
```

## Best Practices

### 1. Always Check Inventory
```python
inventory = build_inventory(targets, customer_id=customer_id)
if not inventory.hosts:
    js.append_log(job, level="ERROR", message="No devices matched targets")
    js.set_status(job, "failed")
    return
```

### 2. Handle Partial Success
```python
# Continue processing even if some hosts fail
results = nr.run(task_function)
for host, r in results.items():
    _log_host_result(js, job, host, r)
    # Don't stop on first failure
```

### 3. Set Appropriate Timeouts
```python
# For long-running commands
results = nr.run(
    netmiko_send_command,
    command_string="show tech-support",
    timeout=300  # 5 minutes
)
```

### 4. Use Connection Options
```python
# Connection options are set automatically in build_inventory
# Includes:
# - Netmiko: fast_cli=True
# - NAPALM: timeout=30
```

### 5. Log Progress
```python
js.append_log(job, level="INFO", message="Starting task execution")
js.append_log(job, level="INFO", host="router1", message="Processing router1")
js.append_log(job, level="INFO", message="Task completed")
```

### 6. Store Results Appropriately
```python
# Store in job result_summary_json
js.set_status(
    job,
    "success",
    result_summary={
        "devices_processed": len(results),
        "success_count": success_count,
        "failure_count": failure_count
    }
)
```

## Examples

### Command Execution Task
```python
@shared_task(name="run_commands_job")
def run_commands_job(job_id: int, targets: dict, commands: list[str], timeout: int = 30):
    js = JobService()
    job = Job.objects.get(pk=job_id)
    js.set_status(job, "running")
    
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched")
        js.set_status(job, "failed")
        return
    
    nr = Nornir(inventory=inventory, runner=ThreadedRunner())
    
    for cmd in commands:
        res = nr.run(netmiko_send_command, command_string=cmd, timeout=timeout)
        for host, r in res.items():
            _log_host_result(js, job, host, r)
    
    js.set_status(job, "success")
```

### Config Backup Task
```python
@shared_task(name="config_backup_job")
def config_backup_job(job_id: int, targets: dict, source_label: str = "manual"):
    js = JobService()
    job = Job.objects.get(pk=job_id)
    js.set_status(job, "running")
    
    inventory = build_inventory(targets, customer_id=job.customer_id)
    nr = Nornir(inventory=inventory, runner=ThreadedRunner())
    
    res = nr.run(napalm_get, getters=["config"])
    
    for host, r in res.items():
        if r.failed:
            _log_host_result(js, job, host, r)
            continue
        
        config = (r.result.get("config") or {}).get("running") or ""
        device = Device.objects.filter(hostname=host, customer=job.customer).first()
        
        if device:
            ConfigSnapshot.objects.create(
                device=device,
                job=job,
                source=source_label,
                config_text=config
            )
    
    js.set_status(job, "success")
```

## References

- [Nornir Documentation](https://nornir.readthedocs.io/)
- [Netmiko Documentation](https://github.com/ktbyers/netmiko)
- [NAPALM Documentation](https://napalm.readthedocs.io/)
- [Celery Tasks](./snippets.md#celery-tasks)

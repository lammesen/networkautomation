"""Network API endpoints for ad-hoc device operations.

These endpoints allow executing commands on devices without requiring them
to be registered in the database. Device credentials are provided directly
in the request payload.
"""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.automation.tasks_network import (
    CommandRequest,
    ComplianceRequest,
    ReachabilityRequest,
    execute_adhoc_commands,
    execute_adhoc_getters,
    execute_adhoc_reachability,
)
from app.core.auth import get_current_user
from app.db import User

router = APIRouter(prefix="/network", tags=["network"])


@router.post("/run_commands")
async def run_commands_endpoint(
    req: CommandRequest, current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Run CLI commands on devices.

    Accepts a list of devices with credentials and commands to execute.
    Returns command output per device.
    """
    return await run_in_threadpool(execute_adhoc_commands, req)


@router.post("/compliance/getters")
async def run_compliance_endpoint(
    req: ComplianceRequest, current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Run NAPALM getters on devices.

    Accepts a list of devices with credentials and NAPALM getters to execute.
    Returns getter results per device.
    """
    return await run_in_threadpool(execute_adhoc_getters, req)


@router.post("/check_reachability")
async def check_reachability_endpoint(
    req: ReachabilityRequest, current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Check TCP reachability on devices.

    Accepts a list of devices and checks if their SSH port is reachable.
    Returns reachability status per device.
    """
    return await run_in_threadpool(execute_adhoc_reachability, req)

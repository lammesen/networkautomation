"""Command execution API endpoints."""

from fastapi import APIRouter, Depends, Query, status

from app.api import errors
from app.core.auth import require_operator
from app.dependencies import get_job_service, get_operator_context
from app.domain.context import TenantRequestContext
from app.domain.exceptions import DomainError
from app.schemas.job import CommandRunRequest
from app.services.job_service import JobService
from app.celery_app import celery_app

router = APIRouter(prefix="/commands", tags=["commands"])


COMMAND_SUGGESTIONS = {
    "ios": [
        "show version",
        "show ip interface brief",
        "show running-config",
        "show interfaces",
        "show cdp neighbors",
        "show vlan",
        "show ip route",
        "show inventory",
        "show environment",
    ],
    "nxos": [
        "show version",
        "show ip interface brief",
        "show running-config",
        "show interface status",
        "show cdp neighbors",
        "show vlan",
        "show ip route",
        "show inventory",
        "show environment",
        "show port-channel summary",
    ],
    "eos": [
        "show version",
        "show ip interface brief",
        "show running-config",
        "show interfaces status",
        "show lldp neighbors",
        "show vlan",
        "show ip route",
        "show inventory",
        "show environment all",
    ],
    "junos": [
        "show version",
        "show interfaces terse",
        "show configuration",
        "show chassis hardware",
        "show system alarms",
        "show route",
        "show lldp neighbors",
        "show ethernet-switching table",
    ],
}


@router.get("/suggestions", response_model=list[str])
def get_command_suggestions(
    platform: str = Query(..., description="Device platform (e.g., ios, eos)"),
    current_user = Depends(require_operator),
) -> list[str]:
    """Get valid command suggestions for a platform."""
    return COMMAND_SUGGESTIONS.get(platform.lower(), [])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_commands(
    request: CommandRunRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Run commands on target devices."""
    try:
        job = service.create_job(
            job_type="run_commands",
            user=context.user,
            customer_id=context.customer_id,
            target_summary={"filters": request.targets},
            payload={
                "commands": request.commands,
                "timeout": request.timeout_sec,
            },
        )
    except DomainError as exc:
        raise errors.to_http(exc)

    celery_app.send_task(
        "run_commands_job",
        args=[job.id, request.targets, request.commands, request.timeout_sec],
    )

    return {"job_id": job.id, "status": "queued"}

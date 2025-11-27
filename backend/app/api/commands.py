"""Command execution API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status

from app.celery_app import celery_app
from app.core.audit import AuditAction, AuditOutcome, audit_log
from app.core.auth import require_operator
from app.dependencies import get_job_service, get_operator_context
from app.domain.context import TenantRequestContext
from app.schemas.job import CommandRunRequest
from app.services.job_service import JobService

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
    current_user=Depends(require_operator),
) -> list[str]:
    """Get valid command suggestions for a platform."""
    return COMMAND_SUGGESTIONS.get(platform.lower(), [])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_commands(
    request_obj: Request,
    request: CommandRunRequest,
    service: JobService = Depends(get_job_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Run commands on target devices."""
    # Get IP for audit logging
    forwarded_for = request_obj.headers.get("x-forwarded-for")
    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request_obj.client.host if request_obj.client else None)
    )

    eta = None
    scheduled_for = request.execute_at
    now = datetime.utcnow()
    if scheduled_for and scheduled_for > now:
        eta = scheduled_for

    job = service.create_job(
        job_type="run_commands",
        user=context.user,
        customer_id=context.customer_id,
        target_summary={"filters": request.targets},
        payload={
            "commands": request.commands,
            "timeout": request.timeout_sec,
        },
        scheduled_for=scheduled_for,
    )

    celery_app.send_task(
        "run_commands_job",
        args=[job.id, request.targets, request.commands, request.timeout_sec],
        eta=eta,
    )

    # Determine action type
    action = AuditAction.COMMAND_SCHEDULE if eta else AuditAction.COMMAND_EXECUTE

    audit_log(
        action,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=ip_address,
        user_agent=request_obj.headers.get("user-agent"),
        resource_type="job",
        resource_id=str(job.id),
        details={
            "job_type": "run_commands",
            "targets": request.targets,
            "command_count": len(request.commands),
            "commands": request.commands,
            "timeout_sec": request.timeout_sec,
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        },
    )

    return {"job_id": job.id, "status": job.status}

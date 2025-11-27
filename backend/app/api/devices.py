"""Device API endpoints."""

from __future__ import annotations

import codecs
import csv
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.core.audit import AuditAction, AuditOutcome, audit_log, mask_sensitive_data
from app.dependencies import (
    get_credential_service,
    get_device_service,
    get_job_service,
    get_multi_tenant_context,
    get_operator_context,
)
from app.domain.context import MultiTenantContext, TenantRequestContext
from app.domain.devices import DeviceFilters
from app.domain.exceptions import DomainError
from app.domain.jobs import JobFilters
from app.schemas.device import (
    CredentialCreate,
    CredentialResponse,
    CredentialUpdate,
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
)
from app.schemas.job import JobResponse
from app.services.credential_service import CredentialService
from app.services.device_service import DeviceService
from app.services.job_service import JobService

router = APIRouter(prefix="/devices", tags=["devices"])
cred_router = APIRouter(prefix="/credentials", tags=["credentials"])


def _get_ip_address(request: Request) -> str | None:
    """Extract client IP address from request."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


# -----------------------------------------------------------------------------
# Credential endpoints


@cred_router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    request: Request,
    payload: CredentialCreate,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> CredentialResponse:
    """Create a new credential."""
    credential = service.create_credential(payload, context)

    audit_log(
        AuditAction.CREDENTIAL_CREATE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="credential",
        resource_id=str(credential.id),
        resource_name=credential.name,
        new_value=mask_sensitive_data({"name": credential.name, "username": credential.username}),
    )

    return CredentialResponse.model_validate(credential)


@cred_router.get("", response_model=list[CredentialResponse])
def list_credentials(
    service: CredentialService = Depends(get_credential_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> list[CredentialResponse]:
    """List all credentials for accessible customers."""
    credentials = service.list_credentials_multi_tenant(context)
    return [CredentialResponse.model_validate(cred) for cred in credentials]


@cred_router.get("/{credential_id}", response_model=CredentialResponse)
def get_credential(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> CredentialResponse:
    """Get credential by ID."""
    credential = service.get_credential_multi_tenant(credential_id, context)
    return CredentialResponse.model_validate(credential)


@cred_router.put("/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: int,
    request: Request,
    payload: CredentialUpdate,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> CredentialResponse:
    """Update credential."""
    credential = service.update_credential(credential_id, payload, context)

    audit_log(
        AuditAction.CREDENTIAL_UPDATE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="credential",
        resource_id=str(credential.id),
        resource_name=credential.name,
        details={"fields_updated": [k for k, v in payload.model_dump().items() if v is not None]},
    )

    return CredentialResponse.model_validate(credential)


@cred_router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: int,
    request: Request,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> None:
    """Delete credential."""
    # Get credential name before deletion for audit log
    credential = service.get_credential(credential_id, context)
    credential_name = credential.name

    service.delete_credential(credential_id, context)

    audit_log(
        AuditAction.CREDENTIAL_DELETE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="credential",
        resource_id=str(credential_id),
        resource_name=credential_name,
    )


# -----------------------------------------------------------------------------
# Device endpoints


@router.post("/import", status_code=status.HTTP_200_OK)
def import_devices(
    request: Request,
    file: UploadFile = File(...),
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Import devices from CSV file."""
    if not file.filename.endswith(".csv"):
        raise DomainError("File must be a CSV")

    reader = csv.DictReader(codecs.iterdecode(file.file, "utf-8"))
    summary = service.import_devices(reader, context)

    audit_log(
        AuditAction.DEVICE_IMPORT,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="device",
        details={
            "filename": file.filename,
            "created": summary.get("created", 0),
            "updated": summary.get("updated", 0),
            "errors": summary.get("errors", 0),
        },
    )

    return summary


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    request: Request,
    payload: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> DeviceResponse:
    """Create a new device."""
    device = service.create_device(payload, context)

    audit_log(
        AuditAction.DEVICE_CREATE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="device",
        resource_id=str(device.id),
        resource_name=device.hostname,
        new_value={
            "hostname": device.hostname,
            "mgmt_ip": device.mgmt_ip,
            "vendor": device.vendor,
            "platform": device.platform,
            "site": device.site,
            "role": device.role,
        },
    )

    return DeviceResponse.model_validate(device)


@router.get("", response_model=DeviceListResponse)
def list_devices(
    site: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    reachability_status: Optional[str] = Query(
        None, description="Filter by reachability status (reachable/unreachable/unknown)"
    ),
    search: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: DeviceService = Depends(get_device_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> DeviceListResponse:
    """List devices with optional filters.

    If no X-Customer-ID header is provided, returns devices from all
    customers the user has access to.
    """
    filters = DeviceFilters(
        site=site,
        role=role,
        vendor=vendor,
        reachability_status=reachability_status,
        search=search,
        enabled=enabled,
        skip=skip,
        limit=limit,
    )
    total, records = service.list_devices_multi_tenant(filters, context)
    return DeviceListResponse(
        total=total,
        devices=[DeviceResponse.model_validate(device) for device in records],
    )


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> DeviceResponse:
    """Get device by ID."""
    device = service.get_device_multi_tenant(device_id, context)
    return DeviceResponse.model_validate(device)


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int,
    request: Request,
    payload: DeviceUpdate,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> DeviceResponse:
    """Update device."""
    device = service.update_device(device_id, payload, context)

    audit_log(
        AuditAction.DEVICE_UPDATE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="device",
        resource_id=str(device.id),
        resource_name=device.hostname,
        details={"fields_updated": [k for k, v in payload.model_dump().items() if v is not None]},
    )

    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    request: Request,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> None:
    """Disable device (soft delete)."""
    # Get device info before deletion for audit log
    device = service.get_device(device_id, context)
    hostname = device.hostname

    service.disable_device(device_id, context)

    audit_log(
        AuditAction.DEVICE_DELETE,
        AuditOutcome.SUCCESS,
        user_id=context.user.id,
        username=context.user.username,
        user_role=context.user.role,
        customer_id=context.customer_id,
        customer_name=context.customer.name,
        ip_address=_get_ip_address(request),
        user_agent=request.headers.get("user-agent"),
        resource_type="device",
        resource_id=str(device_id),
        resource_name=hostname,
    )


@router.get("/{device_id}/jobs", response_model=list[JobResponse])
def list_device_jobs(
    device_id: int,
    job_type: Optional[str] = Query(None, alias="type"),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    device_service: DeviceService = Depends(get_device_service),
    job_service: JobService = Depends(get_job_service),
    context: MultiTenantContext = Depends(get_multi_tenant_context),
) -> list[JobResponse]:
    """List jobs that targeted a specific device."""
    # First get the device to get its hostname and verify access
    device = device_service.get_device_multi_tenant(device_id, context)

    filters = JobFilters(job_type=job_type, status=status, skip=skip, limit=limit)
    jobs = job_service.list_jobs_for_device_multi_tenant(device.hostname, filters, context)
    return [JobResponse.model_validate(job) for job in jobs]

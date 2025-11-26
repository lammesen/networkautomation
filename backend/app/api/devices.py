"""Device API endpoints."""

from __future__ import annotations

import codecs
import csv
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.dependencies import (
    get_credential_service,
    get_device_service,
    get_operator_context,
    get_tenant_context,
)
from app.domain.context import TenantRequestContext
from app.domain.devices import DeviceFilters
from app.domain.exceptions import DomainError
from app.schemas.device import (
    CredentialCreate,
    CredentialResponse,
    CredentialUpdate,
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
)
from app.services.credential_service import CredentialService
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])
cred_router = APIRouter(prefix="/credentials", tags=["credentials"])


# -----------------------------------------------------------------------------
# Credential endpoints


@cred_router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialCreate,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> CredentialResponse:
    """Create a new credential."""
    credential = service.create_credential(payload, context)
    return CredentialResponse.model_validate(credential)


@cred_router.get("", response_model=list[CredentialResponse])
def list_credentials(
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> list[CredentialResponse]:
    """List all credentials for the active customer."""
    credentials = service.list_credentials(context)
    return [CredentialResponse.model_validate(cred) for cred in credentials]


@cred_router.get("/{credential_id}", response_model=CredentialResponse)
def get_credential(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> CredentialResponse:
    """Get credential by ID."""
    credential = service.get_credential(credential_id, context)
    return CredentialResponse.model_validate(credential)


@cred_router.put("/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: int,
    payload: CredentialUpdate,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> CredentialResponse:
    """Update credential."""
    credential = service.update_credential(credential_id, payload, context)
    return CredentialResponse.model_validate(credential)


@cred_router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> None:
    """Delete credential."""
    service.delete_credential(credential_id, context)


# -----------------------------------------------------------------------------
# Device endpoints


@router.post("/import", status_code=status.HTTP_200_OK)
def import_devices(
    file: UploadFile = File(...),
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> dict:
    """Import devices from CSV file."""
    if not file.filename.endswith(".csv"):
        raise DomainError("File must be a CSV")

    reader = csv.DictReader(codecs.iterdecode(file.file, "utf-8"))
    summary = service.import_devices(reader, context)
    return summary


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> DeviceResponse:
    """Create a new device."""
    device = service.create_device(payload, context)
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
    context: TenantRequestContext = Depends(get_tenant_context),
) -> DeviceListResponse:
    """List devices with optional filters."""
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
    total, records = service.list_devices(filters, context)
    return DeviceListResponse(
        total=total,
        devices=[DeviceResponse.model_validate(device) for device in records],
    )


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_tenant_context),
) -> DeviceResponse:
    """Get device by ID."""
    device = service.get_device(device_id, context)
    return DeviceResponse.model_validate(device)


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> DeviceResponse:
    """Update device."""
    device = service.update_device(device_id, payload, context)
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
    context: TenantRequestContext = Depends(get_operator_context),
) -> None:
    """Disable device (soft delete)."""
    service.disable_device(device_id, context)

"""Device API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.auth import get_current_user, require_operator
from app.db import get_db, Device, User, Credential
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
)

router = APIRouter(prefix="/devices", tags=["devices"])
cred_router = APIRouter(prefix="/credentials", tags=["credentials"])


# Credential endpoints
@cred_router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    credential: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> CredentialResponse:
    """Create a new credential."""
    existing = db.query(Credential).filter(Credential.name == credential.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential with this name already exists",
        )
    
    db_credential = Credential(**credential.model_dump())
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    return CredentialResponse.model_validate(db_credential)


@cred_router.get("", response_model=list[CredentialResponse])
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CredentialResponse]:
    """List all credentials."""
    credentials = db.query(Credential).all()
    return [CredentialResponse.model_validate(c) for c in credentials]


@cred_router.get("/{credential_id}", response_model=CredentialResponse)
def get_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CredentialResponse:
    """Get credential by ID."""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    return CredentialResponse.model_validate(credential)


# Device endpoints
@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> DeviceResponse:
    """Create a new device."""
    existing = db.query(Device).filter(Device.hostname == device.hostname).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with this hostname already exists",
        )
    
    # Verify credential exists
    credential = db.query(Credential).filter(Credential.id == device.credentials_ref).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    
    db_device = Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return DeviceResponse.model_validate(db_device)


@router.get("", response_model=DeviceListResponse)
def list_devices(
    site: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceListResponse:
    """List devices with optional filters."""
    query = db.query(Device)
    
    if site:
        query = query.filter(Device.site == site)
    if role:
        query = query.filter(Device.role == role)
    if vendor:
        query = query.filter(Device.vendor == vendor)
    if enabled is not None:
        query = query.filter(Device.enabled == enabled)
    if search:
        query = query.filter(
            or_(
                Device.hostname.ilike(f"%{search}%"),
                Device.mgmt_ip.ilike(f"%{search}%"),
            )
        )
    
    total = query.count()
    devices = query.offset(skip).limit(limit).all()
    
    return DeviceListResponse(
        total=total,
        devices=[DeviceResponse.model_validate(d) for d in devices],
    )


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceResponse:
    """Get device by ID."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return DeviceResponse.model_validate(device)


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> DeviceResponse:
    """Update device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    update_data = device_update.model_dump(exclude_unset=True)
    
    # Check if updating hostname and it conflicts
    if "hostname" in update_data:
        existing = (
            db.query(Device)
            .filter(Device.hostname == update_data["hostname"], Device.id != device_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device with this hostname already exists",
            )
    
    # Verify credential if updating
    if "credentials_ref" in update_data:
        credential = db.query(Credential).filter(Credential.id == update_data["credentials_ref"]).first()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found",
            )
    
    for key, value in update_data.items():
        setattr(device, key, value)
    
    db.commit()
    db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> None:
    """Delete device (soft delete by disabling)."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    
    device.enabled = False
    db.commit()

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, role_required
from app.db.session import get_db
from app.devices.models import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[DeviceRead])
def list_devices(
    db: Session = Depends(get_db),
    site: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    vendor: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=True),
):
    query = db.query(Device)
    if site:
        query = query.filter(Device.site == site)
    if role:
        query = query.filter(Device.role == role)
    if vendor:
        query = query.filter(Device.vendor == vendor)
    if tag:
        query = query.filter(Device.tags.contains(tag))
    if search:
        query = query.filter(
            (Device.hostname.ilike(f"%{search}%")) | (Device.mgmt_ip.ilike(f"%{search}%"))
        )
    if enabled is not None:
        query = query.filter(Device.enabled.is_(enabled))
    return query.order_by(Device.hostname).all()


@router.post("", response_model=DeviceRead, dependencies=[Depends(role_required("operator", "admin"))])
def create_device(device: DeviceCreate, db: Session = Depends(get_db)) -> Device:
    new_device = Device(**device.model_dump())
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404)
    return device


@router.put(
    "/{device_id}",
    response_model=DeviceRead,
    dependencies=[Depends(role_required("operator", "admin"))],
)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    db.commit()
    db.refresh(device)
    return device


@router.delete(
    "/{device_id}", dependencies=[Depends(role_required("admin"))], status_code=204
)
def delete_device(device_id: int, db: Session = Depends(get_db)) -> None:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404)
    db.delete(device)
    db.commit()

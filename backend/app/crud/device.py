from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models import Device
from app.schemas.device import DeviceCreate, DeviceUpdate


def get_device(db: Session, device_id: int) -> Optional[Device]:
    return db.query(Device).filter(Device.id == device_id).first()


def get_devices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    site: Optional[str] = None,
    role: Optional[str] = None,
    vendor: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Device]:
    query = db.query(Device)
    if site:
        query = query.filter(Device.site == site)
    if role:
        query = query.filter(Device.role == role)
    if vendor:
        query = query.filter(Device.vendor == vendor)
    if tag:
        query = query.filter(Device.tags.contains([tag]))
    if search:
        query = query.filter(Device.hostname.contains(search))
    return query.offset(skip).limit(limit).all()


def create_device(db: Session, device: DeviceCreate) -> Device:
    db_device = Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def update_device(db: Session, db_device: Device, device_in: DeviceUpdate) -> Device:
    update_data = device_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_device, field, value)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, db_device: Device) -> Device:
    db_device.enabled = False
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

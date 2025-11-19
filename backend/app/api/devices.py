from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import device as crud_device
from app.db.session import get_db
from app.api.auth import require_role
from app.db.models import UserRole

router = APIRouter()


@router.get("/", response_model=List[schemas.device.Device])
def read_devices(
    skip: int = 0,
    limit: int = 100,
    site: Optional[str] = None,
    role: Optional[str] = None,
    vendor: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    return crud_device.get_devices(
        db,
        skip=skip,
        limit=limit,
        site=site,
        role=role,
        vendor=vendor,
        tag=tag,
        search=search,
    )


@router.get("/{device_id}", response_model=schemas.device.Device)
def read_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.viewer)),
):
    db_device = crud_device.get_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device


@router.post("/", response_model=schemas.device.Device)
def create_device(
    device: schemas.device.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    return crud_device.create_device(db=db, device=device)


@router.put("/{device_id}", response_model=schemas.device.Device)
def update_device(
    device_id: int,
    device: schemas.device.DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.operator)),
):
    db_device = crud_device.get_device(db, device_id=device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    return crud_device.update_device(db=db, db_device=db_device, device_in=device)


@router.delete("/{device_id}", response_model=schemas.device.Device)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.auth.User = Depends(require_role(UserRole.admin)),
):
    db_device = crud_device.get_device(db, device_id=device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    return crud_device.delete_device(db=db, db_device=db_device)

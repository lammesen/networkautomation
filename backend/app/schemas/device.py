from pydantic import BaseModel
from typing import List, Optional


class DeviceBase(BaseModel):
    hostname: str
    mgmt_ip: str
    vendor: str
    platform: str
    role: Optional[str] = None
    site: Optional[str] = None
    tags: Optional[List[str]] = []
    credentials_ref: Optional[str] = None
    enabled: bool = True


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    hostname: Optional[str] = None
    mgmt_ip: Optional[str] = None
    vendor: Optional[str] = None
    platform: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    tags: Optional[List[str]] = None
    credentials_ref: Optional[str] = None
    enabled: Optional[bool] = None


class Device(DeviceBase):
    id: int

    class Config:
        from_attributes = True

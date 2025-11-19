from __future__ import annotations

from datetime import datetime
from typing import Optional

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceBase(BaseModel):
    hostname: str
    mgmt_ip: str
    vendor: Optional[str] = None
    platform: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    tags: Optional[str] = None
    credentials_id: Optional[int] = Field(default=None)
    enabled: bool = True
    napalm_driver: Optional[str] = None
    netmiko_device_type: Optional[str] = None
    port: Optional[int] = 22
    metadata_json: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    hostname: Optional[str] = None
    mgmt_ip: Optional[str] = None
    vendor: Optional[str] = None
    platform: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    tags: Optional[str] = None
    credentials_id: Optional[int] = None
    enabled: Optional[bool] = None
    napalm_driver: Optional[str] = None
    netmiko_device_type: Optional[str] = None
    port: Optional[int] = None
    metadata_json: Optional[str] = None


class DeviceRead(DeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

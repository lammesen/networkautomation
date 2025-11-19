from __future__ import annotations

import json
from typing import Iterable

from nornir import InitNornir
from nornir.core.inventory import Inventory, Hosts, Groups, Defaults, Host
from sqlalchemy.orm import Session

from app.automation.netbox_inventory import build_inventory_from_netbox, NetBoxInventoryError
from app.core.config import settings
from app.core.credentials import resolve_credentials_for_device
from app.devices.models import Device


def _device_to_host(device: Device) -> Host:
    metadata = json.loads(device.metadata_json) if device.metadata_json else {}
    data = {
        "platform": device.platform,
        "vendor": device.vendor,
        "role": device.role,
        "site": device.site,
        "tags": (device.tags or "").split(",") if device.tags else [],
        "napalm_driver": device.napalm_driver,
        "netmiko_device_type": device.netmiko_device_type,
        "metadata": metadata,
    }
    username = None
    password = None
    if device.credentials:
        username, password = resolve_credentials_for_device(None, device)  # type: ignore[arg-type]
    host = Host(
        name=device.hostname,
        hostname=device.mgmt_ip,
        username=username,
        password=password,
        port=device.port or 22,
        data=data,
    )
    return host


def inventory_from_db(db: Session, device_ids: Iterable[int] | None = None) -> Inventory:
    query = db.query(Device).filter(Device.enabled.is_(True))
    if device_ids:
        query = query.filter(Device.id.in_(list(device_ids)))
    hosts = Hosts({device.hostname: _device_to_host(device) for device in query.all()})
    return Inventory(hosts=hosts, groups=Groups({}), defaults=Defaults())


def init_nornir_from_db(db: Session, device_ids: Iterable[int] | None = None):
    inventory: Inventory
    if settings.netbox_url and settings.netbox_token:
        try:
            inventory = build_inventory_from_netbox()
        except NetBoxInventoryError:
            inventory = inventory_from_db(db, device_ids)
    else:
        inventory = inventory_from_db(db, device_ids)
    return InitNornir(inventory=inventory)

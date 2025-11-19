from __future__ import annotations

import pynetbox
from nornir.core.inventory import Defaults, Groups, Host, Hosts, Inventory

from app.core.config import settings


class NetBoxInventoryError(Exception):
    pass


def _client() -> pynetbox.api:
    if not settings.netbox_url or not settings.netbox_token:
        raise NetBoxInventoryError("NetBox is not configured")
    return pynetbox.api(url=settings.netbox_url, token=settings.netbox_token, ssl_verify=settings.netbox_tls_verify)


def _host_from_device(device: dict) -> Host:
    primary_ip = device.get("primary_ip4") or device.get("primary_ip")
    mgmt_ip = primary_ip.get("address").split("/")[0] if primary_ip else None
    if not mgmt_ip:
        raise NetBoxInventoryError(f"Device {device.get('name')} missing management IP")
    platform = device.get("platform") or {}
    platform_slug = platform.get("slug") if isinstance(platform, dict) else None
    data = {
        "platform": platform_slug,
        "role": (device.get("device_role") or {}).get("slug") if isinstance(device.get("device_role"), dict) else None,
        "site": (device.get("site") or {}).get("slug") if isinstance(device.get("site"), dict) else None,
        "tags": [tag.get("slug") for tag in device.get("tags", []) if isinstance(tag, dict)],
    }
    return Host(name=device["name"], hostname=mgmt_ip, data=data)


def build_inventory_from_netbox() -> Inventory:
    client = _client()
    devices = client.dcim.devices.filter(status="active")
    hosts = {}
    for device in devices:
        host = _host_from_device(dict(device))
        hosts[host.name] = host
    return Inventory(hosts=Hosts(hosts), groups=Groups({}), defaults=Defaults())

"""Custom Nornir inventory plugin that reads from database."""

from typing import Any, Dict
from nornir.core.inventory import (
    Inventory,
    Groups,
    Hosts,
    Host,
    Group,
    Defaults,
    ConnectionOptions,
)
from app.db import SessionLocal, Device
from app.core.crypto import decrypt_text


def get_nornir_inventory() -> Inventory:
    """Create Nornir inventory from database."""
    db = SessionLocal()
    
    try:
        devices = db.query(Device).filter(Device.enabled.is_(True)).all()
        
        hosts = {}
        groups: Dict[str, Group] = {}
        
        for device in devices:
            # Map vendor/platform to NAPALM driver and Netmiko device_type
            driver_map = {
                ("cisco", "ios"): ("ios", "cisco_ios"),
                ("cisco", "iosxe"): ("ios", "cisco_ios"),
                ("cisco", "iosxr"): ("iosxr", "cisco_xr"),
                ("cisco", "nxos"): ("nxos", "cisco_nxos"),
                ("arista", "eos"): ("eos", "arista_eos"),
                ("juniper", "junos"): ("junos", "juniper_junos"),
                ("linux", "linux"): ("linux", "linux"),
            }
            
            key = (device.vendor.lower(), device.platform.lower())
            napalm_driver, netmiko_type = driver_map.get(key, ("ios", "cisco_ios"))
            
            # Get credentials (decrypt at the edge)
            cred = device.credential
            password = decrypt_text(cred.password)
            enable_password = decrypt_text(cred.enable_password)
            secret_password = enable_password or password
            
            # Create host
            host = Host(
                name=device.hostname,
                hostname=device.mgmt_ip,
                platform=napalm_driver,
                data={
                    "device_id": device.id,
                    "vendor": device.vendor,
                    "platform": device.platform,
                    "role": device.role,
                    "site": device.site,
                    "tags": device.tags or {},
                    "netmiko_device_type": netmiko_type,
                },
                connection_options={
                    "napalm": ConnectionOptions(
                        extras={
                            "optional_args": {
                                "secret": secret_password,
                            }
                        }
                    ),
                    "netmiko": ConnectionOptions(
                        extras={
                            "device_type": netmiko_type,
                            "secret": secret_password,
                        }
                    ),
                },
                username=cred.username,
                password=password,
            )
            
            hosts[device.hostname] = host
            
            # Create groups for site and role
            if device.site and device.site not in groups:
                groups[device.site] = Group(name=device.site)
            
            if device.role and device.role not in groups:
                groups[device.role] = Group(name=device.role)
        
        return Inventory(
            hosts=Hosts(hosts),
            groups=Groups(groups),
            defaults=Defaults(),
        )
    
    finally:
        db.close()


def filter_devices_from_db(filters: Dict[str, Any]) -> list[int]:
    """Filter devices based on criteria and return device IDs."""
    db = SessionLocal()
    
    try:
        query = db.query(Device).filter(Device.enabled.is_(True))
        
        if "site" in filters:
            query = query.filter(Device.site == filters["site"])
        
        if "role" in filters:
            query = query.filter(Device.role == filters["role"])
        
        if "vendor" in filters:
            query = query.filter(Device.vendor == filters["vendor"])
        
        if "device_ids" in filters:
            query = query.filter(Device.id.in_(filters["device_ids"]))
        
        devices = query.all()
        return [d.id for d in devices]
    
    finally:
        db.close()

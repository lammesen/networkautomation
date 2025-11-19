from nornir import InitNornir
from nornir.core.inventory import Inventory
from sqlalchemy.orm import Session

from app.db.models import Device, Credential


def db_inventory(session: Session) -> Inventory:
    devices = session.query(Device).filter(Device.enabled == True).all()
    hosts = {}
    groups = {}
    defaults = {"data": {}}

    for device in devices:
        host_data = {
            "hostname": device.mgmt_ip,
            "platform": device.platform,
            "data": {
                "vendor": device.vendor,
                "role": device.role,
                "site": device.site,
                "tags": device.tags,
            },
        }
        if device.credential:
            host_data["username"] = device.credential.username
            host_data["password"] = device.credential.password
        hosts[device.hostname] = host_data

    return {"hosts": hosts, "groups": groups, "defaults": defaults}


def init_nornir(session: Session) -> InitNornir:
    inventory = db_inventory(session)
    return InitNornir(
        inventory={"plugin": "SimpleInventory", "options": inventory},
        runner={"plugin": "threaded", "options": {"num_workers": 100}},
    )

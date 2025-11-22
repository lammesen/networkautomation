"""Nornir initialization utilities."""

from nornir import InitNornir
from nornir.core import Nornir

from .inventory import get_nornir_inventory


def init_nornir(num_workers: int = 10) -> Nornir:
    """Initialize Nornir with database-backed inventory."""
    inventory = get_nornir_inventory()
    
    nr = InitNornir(
        runner={
            "plugin": "threaded",
            "options": {
                "num_workers": num_workers,
            },
        },
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": {k: v.dict() for k, v in inventory.hosts.items()},
                "groups": {k: v.dict() for k, v in inventory.groups.items()},
                "defaults": inventory.defaults.dict(),
            },
        },
    )
    
    return nr


def filter_nornir_hosts(nr: Nornir, device_ids: list[int]) -> Nornir:
    """Filter Nornir inventory to only include specified device IDs."""
    def filter_func(host):
        return host.data.get("device_id") in device_ids
    
    return nr.filter(filter_func=filter_func)

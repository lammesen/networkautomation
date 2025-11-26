"""Nornir initialization utilities."""

from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.inventory import Defaults, Groups, Hosts, Inventory
from nornir.core.plugins.inventory import InventoryPluginRegister, InventoryPlugin

from .inventory import get_nornir_inventory


class DbInventoryPlugin(InventoryPlugin):
    """Inventory plugin that delegates to our DB-backed builder."""

    def __init__(self, **kwargs):
        pass

    def load(self) -> Inventory:
        return get_nornir_inventory()


# Register plugin name used below
InventoryPluginRegister.register("DbInventory", DbInventoryPlugin)


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
            "plugin": "DbInventory",
            "options": {},
        },
    )

    return nr


def filter_nornir_hosts(nr: Nornir, device_ids: list[int]) -> Nornir:
    """Filter Nornir inventory to only include specified device IDs."""

    def filter_func(host):
        return host.data.get("device_id") in device_ids

    return nr.filter(filter_func=filter_func)

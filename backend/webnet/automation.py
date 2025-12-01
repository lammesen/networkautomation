"""Utility to build Nornir inventory from Django models."""

from __future__ import annotations

from typing import Dict


try:  # pragma: no cover - optional dependency for tests
    from nornir.core import Nornir
    from nornir.core.connections import ConnectionOptions
    from nornir.core.inventory import Inventory, Hosts, Groups, Defaults, Host
except ImportError:  # pragma: no cover - lightweight fallback for tests

    class Nornir:  # type: ignore
        def __init__(self, inventory=None, runner=None):
            self.inventory = inventory
            self.runner = runner

    class ConnectionOptions:  # type: ignore
        def __init__(self, extras=None):
            self.extras = extras or {}

    class Host:  # type: ignore
        def __init__(
            self,
            *,
            name,
            hostname,
            platform,
            groups,
            username,
            password,
            extras,
            connection_options,
        ):
            self.name = name
            self.hostname = hostname
            self.platform = platform
            self.groups = groups
            self.username = username
            self.password = password
            self.extras = extras
            self.connection_options = connection_options

    class Hosts(dict):
        pass

    class Groups(dict):
        pass

    class Defaults(dict):
        pass

    class Inventory:  # type: ignore
        def __init__(self, hosts, groups=None, defaults=None):
            self.hosts = hosts
            self.groups = groups or {}
            self.defaults = defaults or {}


from webnet.devices.models import Device


def build_inventory(filters: dict | None = None, customer_id: int | None = None) -> Inventory:
    qs = Device.objects.select_related("credential", "customer").filter(enabled=True)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if filters:
        if filters.get("device_ids"):
            qs = qs.filter(id__in=filters["device_ids"])
        if filters.get("vendor"):
            qs = qs.filter(vendor=filters["vendor"])
        if filters.get("site"):
            qs = qs.filter(site=filters["site"])
    hosts: Dict[str, Host] = {}
    for dev in qs:
        cred = dev.credential
        hosts[dev.hostname] = Host(
            name=dev.hostname,
            hostname=dev.mgmt_ip,
            platform=dev.platform,
            groups=set(),
            username=cred.username,
            password=cred.password or "",
            extras={
                "customer_id": dev.customer_id,
                "device_id": dev.id,
                "role": dev.role,
                "site": dev.site,
                "vendor": dev.vendor,
            },
            connection_options={
                "netmiko": ConnectionOptions(extras={"fast_cli": True}),
                "napalm": ConnectionOptions(extras={"optional_args": {"timeout": 30}}),
            },
        )
    return Inventory(Hosts(hosts), Groups({}), Defaults())

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict

from napalm import get_network_driver
from napalm.base.base import NetworkDriver

from app.core.config import settings


class DryRunDevice:
    """Simple mock device used when DRY_RUN_MODE is enabled."""

    def __init__(self, hostname: str) -> None:
        self.hostname = hostname
        self._candidate: str | None = None

    def open(self) -> None:  # pragma: no cover - noop
        return None

    def close(self) -> None:  # pragma: no cover - noop
        return None

    def get_config(self) -> Dict[str, str]:
        return {
            "running": f"! simulated running-config for {self.hostname}\ninterface Loopback0\n description dry-run",
        }

    def load_merge_candidate(self, config: str) -> None:
        self._candidate = config

    def compare_config(self) -> str:
        if not self._candidate:
            return ""
        return f"+ {self._candidate.strip()}\n"

    def discard_config(self) -> None:
        self._candidate = None

    def commit_config(self) -> str:
        committed = self._candidate or ""
        self._candidate = None
        return committed

    def compliance_report(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "complies": True,
            "details": policy,
        }


def _build_driver(hostname: str, username: str | None, password: str | None, driver_name: str, optional_args: Dict[str, Any]) -> NetworkDriver | DryRunDevice:
    if settings.dry_run_mode:
        device = DryRunDevice(hostname)
        device.open()
        return device
    driver_cls = get_network_driver(driver_name)
    device = driver_cls(
        hostname=hostname,
        username=username,
        password=password,
        optional_args=optional_args,
    )
    device.open()
    return device


@contextmanager
def napalm_device(task_host) -> Any:
    driver_name = task_host.data.get("napalm_driver") or task_host.platform or "ios"
    optional_args = task_host.data.get("metadata", {}).get("napalm_optional_args", {})
    device = _build_driver(
        hostname=task_host.hostname,
        username=task_host.username,
        password=task_host.password,
        driver_name=driver_name,
        optional_args=optional_args,
    )
    try:
        yield device
    finally:
        device.close()

"""Reusable automation context for Celery jobs."""

from __future__ import annotations

from typing import Dict, List, Optional

from nornir.core import Nornir

from app.automation.inventory import filter_devices_from_db
from app.automation.nornir_init import filter_nornir_hosts, init_nornir
from app.services.job_service import JobService


class AutomationContext:
    """Wraps repeated automation boilerplate."""

    def __init__(
        self,
        *,
        job_id: int,
        targets: Dict,
        job_service: JobService,
        customer_id: Optional[int] = None,
    ) -> None:
        self.job_id = job_id
        self.targets = targets or {}
        self.job_service = job_service
        self.customer_id = customer_id
        self.device_ids: List[int] = []

    def select_devices(self) -> List[int]:
        self.device_ids = filter_devices_from_db(self.targets, customer_id=self.customer_id)
        return self.device_ids

    def log(self, level: str, message: str, host: Optional[str] = None, extra: Optional[dict] = None) -> None:
        self.job_service.append_log(
            self.job_id,
            level=level,
            message=message,
            host=host,
            extra=extra,
        )

    def nornir(self, num_workers: int = 10) -> Nornir:
        nr = init_nornir(num_workers=num_workers)
        if self.device_ids:
            nr = filter_nornir_hosts(nr, self.device_ids)
        return nr

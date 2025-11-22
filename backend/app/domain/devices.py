"""Device-specific domain helpers."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class DeviceFilters:
    """Filters accepted by the device listing endpoint."""

    site: Optional[str] = None
    role: Optional[str] = None
    vendor: Optional[str] = None
    search: Optional[str] = None
    enabled: Optional[bool] = None
    skip: int = 0
    limit: int = 100



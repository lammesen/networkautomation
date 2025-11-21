"""Job-specific domain helpers."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class JobFilters:
    job_type: Optional[str] = None
    status: Optional[str] = None
    skip: int = 0
    limit: int = 100



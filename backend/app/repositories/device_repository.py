"""Device persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import Device
from app.domain.devices import DeviceFilters
from app.repositories.base import SQLAlchemyRepository


class DeviceRepository(SQLAlchemyRepository[Device]):
    """Encapsulates all direct Device ORM access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def _customer_query(self, customer_id: int):
        return self.session.query(Device).filter(Device.customer_id == customer_id)

    def _multi_customer_query(self, customer_ids: Sequence[int]):
        """Create a query filtering by multiple customer IDs."""
        return self.session.query(Device).filter(Device.customer_id.in_(customer_ids))

    def list_for_customer(
        self,
        customer_id: int,
        filters: DeviceFilters,
    ) -> Tuple[int, Sequence[Device]]:
        query = self._customer_query(customer_id)
        return self._apply_filters_and_paginate(query, filters)

    def list_for_customers(
        self,
        customer_ids: Sequence[int],
        filters: DeviceFilters,
    ) -> Tuple[int, Sequence[Device]]:
        """List devices for multiple customers."""
        query = self._multi_customer_query(customer_ids)
        return self._apply_filters_and_paginate(query, filters)

    def _apply_filters_and_paginate(
        self,
        query,
        filters: DeviceFilters,
    ) -> Tuple[int, Sequence[Device]]:
        """Apply common filters and pagination to a query."""
        if filters.site:
            query = query.filter(Device.site == filters.site)
        if filters.role:
            query = query.filter(Device.role == filters.role)
        if filters.vendor:
            query = query.filter(Device.vendor == filters.vendor)
        if filters.reachability_status:
            query = query.filter(Device.reachability_status == filters.reachability_status)
        if filters.enabled is not None:
            query = query.filter(Device.enabled == filters.enabled)
        if filters.search:
            like = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Device.hostname.ilike(like),
                    Device.mgmt_ip.ilike(like),
                )
            )

        total = query.count()
        records = (
            query.order_by(Device.hostname.asc()).offset(filters.skip).limit(filters.limit).all()
        )

        return total, records

    def get_by_id(self, device_id: int, customer_id: int) -> Optional[Device]:
        return self._customer_query(customer_id).filter(Device.id == device_id).first()

    def get_by_id_for_customers(
        self, device_id: int, customer_ids: Sequence[int]
    ) -> Optional[Device]:
        """Get a device by ID if it belongs to one of the specified customers."""
        return self._multi_customer_query(customer_ids).filter(Device.id == device_id).first()

    def find_by_hostname(
        self,
        customer_id: int,
        hostname: str,
        *,
        exclude_id: Optional[int] = None,
    ) -> Optional[Device]:
        query = self._customer_query(customer_id).filter(Device.hostname == hostname)
        if exclude_id is not None:
            query = query.filter(Device.id != exclude_id)
        return query.first()

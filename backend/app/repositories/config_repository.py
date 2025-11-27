"""Config snapshot persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence, Union

from sqlalchemy.orm import Session

from app.db import ConfigSnapshot, Device
from app.repositories.base import SQLAlchemyRepository


class ConfigSnapshotRepository(SQLAlchemyRepository[ConfigSnapshot]):
    """Encapsulates all direct ConfigSnapshot ORM access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_id(self, snapshot_id: int) -> Optional[ConfigSnapshot]:
        return self.session.query(ConfigSnapshot).filter(ConfigSnapshot.id == snapshot_id).first()

    def get_by_id_for_customer(
        self, snapshot_id: int, customer_id: int
    ) -> Optional[ConfigSnapshot]:
        """Get snapshot by ID, verifying customer ownership via device."""
        return (
            self.session.query(ConfigSnapshot)
            .join(ConfigSnapshot.device)
            .filter(
                ConfigSnapshot.id == snapshot_id,
                Device.customer_id == customer_id,
            )
            .first()
        )

    def list_for_device(
        self,
        device_id: int,
        limit: int = 100,
    ) -> Sequence[ConfigSnapshot]:
        return (
            self.session.query(ConfigSnapshot)
            .filter(ConfigSnapshot.device_id == device_id)
            .order_by(ConfigSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_device_with_customer_check(self, device_id: int, customer_id: int) -> Optional[Device]:
        """Get device by ID, filtered by customer."""
        return (
            self.session.query(Device)
            .filter(
                Device.id == device_id,
                Device.customer_id == customer_id,
            )
            .first()
        )

    def get_by_id_for_customers(
        self, snapshot_id: int, customer_ids: Sequence[int]
    ) -> Optional[ConfigSnapshot]:
        """Get snapshot by ID, verifying customer ownership via device for multiple customers."""
        return (
            self.session.query(ConfigSnapshot)
            .join(ConfigSnapshot.device)
            .filter(
                ConfigSnapshot.id == snapshot_id,
                Device.customer_id.in_(customer_ids),
            )
            .first()
        )

    def get_device_with_customers_check(
        self, device_id: int, customer_ids: Sequence[int]
    ) -> Optional[Device]:
        """Get device by ID, filtered by multiple customers."""
        return (
            self.session.query(Device)
            .filter(
                Device.id == device_id,
                Device.customer_id.in_(customer_ids),
            )
            .first()
        )

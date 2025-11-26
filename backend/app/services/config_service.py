"""Configuration management service layer."""

from __future__ import annotations

import difflib
from typing import Sequence

from sqlalchemy.orm import Session

from app.db import ConfigSnapshot
from app.domain.context import TenantRequestContext
from app.domain.exceptions import NotFoundError, ValidationError
from app.repositories import ConfigSnapshotRepository


class ConfigService:
    """Business logic for configuration snapshot operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.snapshots = ConfigSnapshotRepository(session)

    def get_snapshot(
        self,
        snapshot_id: int,
        context: TenantRequestContext,
    ) -> ConfigSnapshot:
        """Get a configuration snapshot by ID, verifying tenant access."""
        snapshot = self.snapshots.get_by_id(snapshot_id)
        if not snapshot:
            raise NotFoundError("Snapshot not found")

        # Verify tenancy via device
        if snapshot.device.customer_id != context.customer_id:
            raise NotFoundError("Snapshot not found")  # Mask as not found for security

        return snapshot

    def list_device_snapshots(
        self,
        device_id: int,
        context: TenantRequestContext,
        limit: int = 100,
    ) -> Sequence[ConfigSnapshot]:
        """List configuration snapshots for a device."""
        device = self.snapshots.get_device_with_customer_check(device_id, context.customer_id)
        if not device:
            raise NotFoundError("Device not found")

        return self.snapshots.list_for_device(device_id, limit=limit)

    def get_config_diff(
        self,
        device_id: int,
        from_snapshot_id: int,
        to_snapshot_id: int,
        context: TenantRequestContext,
    ) -> dict:
        """Get diff between two configuration snapshots."""
        # Verify device access
        device = self.snapshots.get_device_with_customer_check(device_id, context.customer_id)
        if not device:
            raise NotFoundError("Device not found")

        # Get both snapshots
        snapshot_from = self.snapshots.get_by_id(from_snapshot_id)
        snapshot_to = self.snapshots.get_by_id(to_snapshot_id)

        if not snapshot_from or not snapshot_to:
            raise NotFoundError("One or both snapshots not found")

        if snapshot_from.device_id != device_id or snapshot_to.device_id != device_id:
            raise ValidationError("Snapshots must belong to the specified device")

        # Generate diff
        from_lines = snapshot_from.config_text.splitlines(keepends=True)
        to_lines = snapshot_to.config_text.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                from_lines,
                to_lines,
                fromfile=f"Snapshot {from_snapshot_id}",
                tofile=f"Snapshot {to_snapshot_id}",
            )
        )

        return {
            "device_id": device_id,
            "from_snapshot": from_snapshot_id,
            "to_snapshot": to_snapshot_id,
            "diff": "".join(diff),
        }

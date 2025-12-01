"""WebSocket broadcast utilities for real-time UI updates."""

from __future__ import annotations

from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_entity_update(
    *,
    entity: str,
    action: str,
    entity_id: int,
    customer_id: Optional[int] = None,
    html: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Broadcast an entity update to WebSocket clients.

    Args:
        entity: Type of entity (job, device, config, compliance, topology)
        action: What happened (created, updated, deleted)
        entity_id: Primary key of the entity
        customer_id: Customer ID for scoping (None = global/admin only)
        html: Optional pre-rendered HTML partial for HTMX swap
        extra: Optional extra data to include in message
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    data = {
        "type": "update",
        "entity": entity,
        "action": action,
        "id": entity_id,
    }
    if html:
        data["html"] = html
    if extra:
        data.update(extra)

    message = {"type": "entity_update", "data": data}

    try:
        if customer_id:
            # Send to customer-specific group
            group = f"updates_customer_{customer_id}"
            async_to_sync(channel_layer.group_send)(group, message)
        else:
            # Send to global group (admins only)
            async_to_sync(channel_layer.group_send)("updates_global", message)
    except Exception:
        # Don't break on broadcast failures
        pass


def broadcast_job_update(job, action: str = "updated") -> None:
    """Convenience function to broadcast job updates."""
    broadcast_entity_update(
        entity="job",
        action=action,
        entity_id=job.id,
        customer_id=job.customer_id,
        extra={
            "status": job.status,
            "job_type": job.type,
        },
    )


def broadcast_device_update(device, action: str = "updated") -> None:
    """Convenience function to broadcast device updates."""
    broadcast_entity_update(
        entity="device",
        action=action,
        entity_id=device.id,
        customer_id=device.customer_id,
        extra={
            "hostname": device.hostname,
            "reachability_status": device.reachability_status,
        },
    )


def broadcast_config_update(snapshot, action: str = "created") -> None:
    """Convenience function to broadcast config snapshot updates."""
    broadcast_entity_update(
        entity="config",
        action=action,
        entity_id=snapshot.id,
        customer_id=snapshot.device.customer_id,
        extra={
            "device_id": snapshot.device_id,
        },
    )


def broadcast_compliance_update(result, action: str = "created") -> None:
    """Convenience function to broadcast compliance result updates."""
    broadcast_entity_update(
        entity="compliance",
        action=action,
        entity_id=result.id,
        customer_id=result.policy.customer_id,
        extra={
            "status": result.status,
            "device_id": result.device_id,
            "policy_id": result.policy_id,
        },
    )


def broadcast_topology_update(link, action: str = "created") -> None:
    """Convenience function to broadcast topology link updates."""
    broadcast_entity_update(
        entity="topology",
        action=action,
        entity_id=link.id,
        customer_id=link.customer_id,
    )

"""Django signals for broadcasting model changes via WebSocket."""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from webnet.devices.models import Device, TopologyLink
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.compliance.models import ComplianceResult
from webnet.core.broadcasts import (
    broadcast_device_update,
    broadcast_config_update,
    broadcast_compliance_update,
    broadcast_topology_update,
)


@receiver(post_save, sender=Device)
def device_saved(sender, instance, created, **kwargs):
    """Broadcast when a device is created or updated."""
    action = "created" if created else "updated"
    broadcast_device_update(instance, action=action)


@receiver(post_delete, sender=Device)
def device_deleted(sender, instance, **kwargs):
    """Broadcast when a device is deleted."""
    broadcast_device_update(instance, action="deleted")


@receiver(post_save, sender=ConfigSnapshot)
def config_snapshot_saved(sender, instance, created, **kwargs):
    """Broadcast when a config snapshot is created."""
    if created:
        broadcast_config_update(instance, action="created")


@receiver(post_save, sender=ComplianceResult)
def compliance_result_saved(sender, instance, created, **kwargs):
    """Broadcast when a compliance result is created."""
    if created:
        broadcast_compliance_update(instance, action="created")


@receiver(post_save, sender=TopologyLink)
def topology_link_saved(sender, instance, created, **kwargs):
    """Broadcast when a topology link is created or updated."""
    action = "created" if created else "updated"
    broadcast_topology_update(instance, action=action)


@receiver(post_delete, sender=TopologyLink)
def topology_link_deleted(sender, instance, **kwargs):
    """Broadcast when a topology link is deleted."""
    broadcast_topology_update(instance, action="deleted")

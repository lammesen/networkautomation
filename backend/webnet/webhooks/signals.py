"""Django signals for triggering webhook events."""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from webnet.devices.models import Device
from webnet.jobs.models import Job
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.compliance.models import ComplianceResult
from webnet.webhooks.tasks import trigger_webhook_event


def _build_job_payload(job: Job) -> dict:
    """Build webhook payload for job events."""
    return {
        "event_timestamp": timezone.now().isoformat(),
        "actor": {"id": job.user_id, "username": job.user.username},
        "job": {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "requested_at": job.requested_at.isoformat() if job.requested_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "target_summary": job.target_summary_json,
            "result_summary": job.result_summary_json,
        },
    }


def _build_device_payload(device: Device, action: str) -> dict:
    """Build webhook payload for device events."""
    return {
        "event_timestamp": timezone.now().isoformat(),
        "action": action,
        "device": {
            "id": device.id,
            "hostname": device.hostname,
            "mgmt_ip": device.mgmt_ip,
            "vendor": device.vendor,
            "platform": device.platform,
            "role": device.role,
            "site": device.site,
            "enabled": device.enabled,
            "reachability_status": device.reachability_status,
        },
    }


def _build_config_payload(snapshot: ConfigSnapshot, event_type: str) -> dict:
    """Build webhook payload for config events."""
    return {
        "event_timestamp": timezone.now().isoformat(),
        "event_type": event_type,
        "config": {
            "id": snapshot.id,
            "device_id": snapshot.device_id,
            "device_hostname": snapshot.device.hostname,
            "timestamp": snapshot.timestamp.isoformat(),
            "source": snapshot.source,
            "has_changed": snapshot.has_changed,
            "config_hash": snapshot.config_hash,
        },
    }


def _build_compliance_payload(result: ComplianceResult) -> dict:
    """Build webhook payload for compliance events."""
    return {
        "event_timestamp": timezone.now().isoformat(),
        "compliance": {
            "id": result.id,
            "device_id": result.device_id,
            "device_hostname": result.device.hostname,
            "policy_id": result.policy_id,
            "policy_name": result.policy.name,
            "status": result.status,
            "timestamp": result.timestamp.isoformat(),
            "violations_count": len(result.violations_json or []),
            "violations": result.violations_json,
        },
    }


@receiver(post_save, sender=Job)
def job_saved(sender, instance, created, **kwargs):
    """Trigger webhook when job is created or status changes."""
    if created:
        event_type = "job.created"
    elif instance.status == "running":
        event_type = "job.started"
    elif instance.status == "success":
        event_type = "job.completed"
    elif instance.status == "failed":
        event_type = "job.failed"
    else:
        # Don't trigger for other status changes
        return

    payload = _build_job_payload(instance)
    trigger_webhook_event.delay(
        customer_id=instance.customer_id,
        event_type=event_type,
        event_id=instance.id,
        payload=payload,
    )


@receiver(post_save, sender=Device)
def device_saved(sender, instance, created, **kwargs):
    """Trigger webhook when device is created or updated."""
    # Track previous reachability status to detect status changes
    if created:
        action = "created"
        event_type = "device.created"
    else:
        # Check if reachability status changed
        try:
            old_instance = Device.objects.get(pk=instance.pk)
            if old_instance.reachability_status != instance.reachability_status:
                event_type = "device.status_changed"
                action = "status_changed"
            else:
                event_type = "device.updated"
                action = "updated"
        except Device.DoesNotExist:
            event_type = "device.updated"
            action = "updated"

    payload = _build_device_payload(instance, action)
    trigger_webhook_event.delay(
        customer_id=instance.customer_id,
        event_type=event_type,
        event_id=instance.id,
        payload=payload,
    )


@receiver(post_delete, sender=Device)
def device_deleted(sender, instance, **kwargs):
    """Trigger webhook when device is deleted."""
    payload = _build_device_payload(instance, "deleted")
    trigger_webhook_event.delay(
        customer_id=instance.customer_id,
        event_type="device.deleted",
        event_id=instance.id,
        payload=payload,
    )


@receiver(post_save, sender=ConfigSnapshot)
def config_snapshot_saved(sender, instance, created, **kwargs):
    """Trigger webhook when config snapshot is created."""
    if not created:
        return

    # Determine event type based on snapshot attributes
    if instance.has_changed:
        event_type = "config.changed"
    else:
        event_type = "config.backup_created"

    # Check if this was part of a deployment
    if instance.source in ["deploy", "template_deploy"]:
        event_type = "config.deployed"

    payload = _build_config_payload(instance, event_type)
    trigger_webhook_event.delay(
        customer_id=instance.device.customer_id,
        event_type=event_type,
        event_id=instance.id,
        payload=payload,
    )


@receiver(post_save, sender=ComplianceResult)
def compliance_result_saved(sender, instance, created, **kwargs):
    """Trigger webhook when compliance check completes."""
    if not created:
        return

    # Always trigger check_completed
    payload = _build_compliance_payload(instance)
    trigger_webhook_event.delay(
        customer_id=instance.policy.customer_id,
        event_type="compliance.check_completed",
        event_id=instance.id,
        payload=payload,
    )

    # Also trigger violation_detected if there are violations
    if instance.status == "fail":
        trigger_webhook_event.delay(
            customer_id=instance.policy.customer_id,
            event_type="compliance.violation_detected",
            event_id=instance.id,
            payload=payload,
        )

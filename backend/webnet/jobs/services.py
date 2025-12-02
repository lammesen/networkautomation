"""Job orchestration service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence, Callable

from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from webnet.jobs.models import Job, JobLog
from webnet.jobs.serializers import JobLogSerializer  # local serializer for WS broadcast
from webnet.users.models import User
from webnet.customers.models import Customer
from webnet.core.celery import celery_app
from webnet.core.broadcasts import broadcast_job_update

logger = logging.getLogger(__name__)


class JobService:
    """Coordinates job lifecycle and dispatch to Celery."""

    def __init__(self, dispatcher: Callable | None = None):
        # dispatcher allows injection/mocking in tests; defaults to celery send_task
        self.dispatcher = dispatcher or celery_app.send_task

    @transaction.atomic
    def create_job(
        self,
        *,
        job_type: str,
        user: User,
        customer: Customer,
        target_summary: Optional[dict] = None,
        payload: Optional[dict] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> Job:
        status = "scheduled" if scheduled_for else "queued"
        job = Job.objects.create(
            type=job_type,
            status=status,
            user=user,
            customer=customer,
            target_summary_json=target_summary,
            payload_json=payload,
            requested_at=datetime.now(timezone.utc),
            scheduled_for=scheduled_for,
        )
        if status == "queued":
            self._enqueue(job)
        # Broadcast job creation
        broadcast_job_update(job, action="created")
        return job

    @transaction.atomic
    def set_status(self, job: Job, status: str, result_summary: Optional[dict] = None) -> Job:
        job.status = status
        if status == "running" and not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        if status in {"success", "partial", "failed", "cancelled"}:
            job.finished_at = datetime.now(timezone.utc)
        if result_summary is not None:
            job.result_summary_json = result_summary
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "result_summary_json",
            ]
        )
        # Broadcast job status change
        broadcast_job_update(job, action="updated")
        return job

    @transaction.atomic
    def append_log(
        self,
        job: Job,
        *,
        level: str,
        message: str,
        host: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> JobLog:
        log = JobLog.objects.create(
            job=job,
            level=level,
            host=host,
            message=message,
            extra_json=extra,
        )
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"job_{job.id}", {"type": "job_log", "data": JobLogSerializer(log).data}
            )
        except Exception as e:
            logger.warning("Failed to broadcast job log for job %s: %s", job.id, e)
        return log

    def list_jobs(self, customer_ids: Sequence[int] | None = None) -> Sequence[Job]:
        qs = Job.objects.all()
        if customer_ids:
            qs = qs.filter(customer_id__in=customer_ids)
        return qs

    def _determine_region(self, job: Job) -> Optional["Region"]:  # type: ignore[name-defined]  # noqa: F821
        """Determine the target region for a job based on devices.

        Returns the region to route to, or None for default queue.
        Implements priority-based selection and health checking.
        """
        from webnet.core.models import Region
        from webnet.devices.models import Device

        # Get target devices from job's target_summary
        # Support both nested {"filters": {...}} and flat {...} formats
        target_filters = (job.target_summary_json or {}).get("filters", {})
        if not target_filters and job.target_summary_json:
            # Fallback: treat top-level keys as filters for backward compatibility
            # This handles compliance jobs which use policy.scope_json directly
            target_filters = job.target_summary_json

        if not target_filters:
            # No specific targets, use default queue
            return None

        # Query devices matching the filters
        devices_qs = Device.objects.filter(customer=job.customer, enabled=True)

        # Apply filters to find target devices
        if target_filters.get("site"):
            devices_qs = devices_qs.filter(site__iexact=target_filters["site"])
        if target_filters.get("role"):
            devices_qs = devices_qs.filter(role__iexact=target_filters["role"])
        if target_filters.get("vendor"):
            devices_qs = devices_qs.filter(vendor__iexact=target_filters["vendor"])
        if target_filters.get("hostname"):
            devices_qs = devices_qs.filter(hostname__iexact=target_filters["hostname"])
        if target_filters.get("device_ids"):
            devices_qs = devices_qs.filter(id__in=target_filters["device_ids"])

        # Get regions from target devices
        device_regions = (
            devices_qs.exclude(region__isnull=True).values_list("region", flat=True).distinct()
        )

        if not device_regions:
            # No devices have regions assigned, use default queue
            return None

        # If multiple regions, select the highest priority available one
        regions = (
            Region.objects.filter(
                id__in=device_regions,
                customer=job.customer,
                enabled=True,
            )
            .exclude(health_status=Region.STATUS_OFFLINE)
            .order_by("-priority", "name")
        )

        if regions.exists():
            selected_region = regions.first()
            logger.info(
                "Routing job %s to region %s (priority=%s, status=%s)",
                job.id,
                selected_region.identifier,
                selected_region.priority,
                selected_region.health_status,
            )
            return selected_region

        # All regions offline or unavailable, log warning and use default queue
        logger.warning(
            "All regions for job %s are offline or unavailable, using default queue",
            job.id,
        )
        return None

    def _enqueue(self, job: Job) -> None:
        task_map = {
            "run_commands": (
                "run_commands_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                    (j.payload_json or {}).get("commands", []),
                    (j.payload_json or {}).get("timeout"),
                ),
            ),
            "config_backup": (
                "config_backup_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                    (j.payload_json or {}).get("source_label", "manual"),
                ),
            ),
            "config_deploy_preview": (
                "config_deploy_preview_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                    (j.payload_json or {}).get("mode"),
                    (j.payload_json or {}).get("snippet", ""),
                ),
            ),
            "config_deploy_commit": (
                "config_deploy_commit_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                    (j.payload_json or {}).get("mode"),
                    (j.payload_json or {}).get("snippet", ""),
                ),
            ),
            "compliance_check": (
                "compliance_check_job",
                lambda j: (j.id, (j.payload_json or {}).get("policy_id")),
            ),
            "topology_discovery": (
                "topology_discovery_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                    (j.payload_json or {}).get("protocol", "both"),
                    (j.payload_json or {}).get("auto_create_devices", False),
                ),
            ),
            "check_reachability": (
                "check_reachability_job",
                lambda j: (
                    j.id,
                    (j.target_summary_json or {}).get("filters", {}),
                ),
            ),
            # Issue #40 - Bulk Device Onboarding job types
            "ip_range_scan": (
                "ip_range_scan_job",
                lambda j: (
                    j.id,
                    (j.payload_json or {}).get("ip_ranges", []),
                    (j.payload_json or {}).get("credential_ids", []),
                    (j.payload_json or {}).get("use_snmp", True),
                    (j.payload_json or {}).get("snmp_community", "public"),
                    (j.payload_json or {}).get("snmp_version", "2c"),
                    (j.payload_json or {}).get("test_ssh", True),
                    (j.payload_json or {}).get("ports", [22]),
                ),
            ),
            "credential_test": (
                "credential_test_job",
                lambda j: (
                    j.id,
                    (j.payload_json or {}).get("discovered_device_ids", []),
                    (j.payload_json or {}).get("credential_ids", []),
                ),
            ),
        }
        entry = task_map.get(job.type)
        if not entry:
            return
        task_name, args_fn = entry

        # Determine target region for job routing
        region = self._determine_region(job)
        queue_name = None

        if region:
            # Update job with assigned region
            job.region = region
            job.save(update_fields=["region"])
            queue_name = region.queue_name
            logger.info(
                "Job %s assigned to region %s (queue=%s)", job.id, region.identifier, queue_name
            )

        try:
            # Send task to appropriate queue
            self.dispatcher(task_name, args=args_fn(job), queue=queue_name)
        except Exception as e:
            logger.error(
                "Failed to enqueue job %s (type=%s, queue=%s): %s", job.id, job.type, queue_name, e
            )
            # leave job queued; caller may retry

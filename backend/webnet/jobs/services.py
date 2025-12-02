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

        # Send ChatOps notifications if job is completed
        if status in {"success", "partial", "failed"}:
            try:
                from webnet.chatops.slack_service import notify_job_completion
                from webnet.chatops.teams_service import notify_job_completion_teams

                notify_job_completion(job)
                notify_job_completion_teams(job)
            except Exception as e:
                logger.warning(f"Failed to send ChatOps notification: {e}")

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
        try:
            self.dispatcher(task_name, args=args_fn(job))
        except Exception as e:
            logger.error("Failed to enqueue job %s (type=%s): %s", job.id, job.type, e)
            # leave job queued; caller may retry

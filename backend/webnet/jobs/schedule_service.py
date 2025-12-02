"""Schedule management service for managing scheduled jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone

from webnet.jobs.models import Schedule, Job
from webnet.jobs.services import JobService

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for managing scheduled jobs."""

    def __init__(self):
        self.job_service = JobService()

    def calculate_next_run(self, schedule: Schedule) -> Optional[datetime]:
        """Calculate the next run time for a schedule."""
        if not schedule.enabled:
            return None
        
        now = timezone.now()
        
        if schedule.interval_type == "hourly":
            return now + timedelta(hours=1)
        elif schedule.interval_type == "daily":
            # Run at 2 AM tomorrow
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif schedule.interval_type == "weekly":
            # Run at 2 AM next Monday
            days_ahead = 7 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=2, minute=0, second=0, microsecond=0)
            return next_run
        elif schedule.interval_type == "monthly":
            # Run at 2 AM on the 1st of next month
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=2, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=2, minute=0, second=0, microsecond=0)
            return next_run
        elif schedule.interval_type == "cron" and schedule.cron_expression:
            # For cron, use a simple parser for common patterns
            # Format: "minute hour day month day_of_week"
            return self._calculate_cron_next_run(schedule.cron_expression, now)
        
        return None

    def _calculate_cron_next_run(self, cron_expr: str, from_time: datetime) -> Optional[datetime]:
        """Simple cron parser for common patterns."""
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                return None
            
            minute, hour, day, month, day_of_week = parts
            
            # For simplicity, handle common patterns
            # "0 2 * * *" = daily at 2 AM
            if minute.isdigit() and hour.isdigit() and day == "*" and month == "*" and day_of_week == "*":
                next_run = from_time.replace(
                    hour=int(hour), 
                    minute=int(minute), 
                    second=0, 
                    microsecond=0
                )
                if next_run <= from_time:
                    next_run += timedelta(days=1)
                return next_run
            
            # Return a default (daily at configured time)
            return from_time + timedelta(days=1)
        except Exception as e:
            logger.error(f"Failed to parse cron expression '{cron_expr}': {e}")
            return None

    def update_next_run(self, schedule: Schedule) -> None:
        """Update the next_run field for a schedule."""
        schedule.next_run = self.calculate_next_run(schedule)
        schedule.save(update_fields=["next_run"])

    def create_scheduled_job(self, schedule: Schedule) -> Optional[Job]:
        """Create a job from a schedule."""
        if not schedule.enabled:
            return None
        
        try:
            job = self.job_service.create_job(
                job_type=schedule.job_type,
                user=schedule.created_by,
                customer=schedule.customer,
                target_summary=schedule.target_summary_json,
                payload=schedule.payload_json,
            )
            
            # Update schedule last_run and next_run
            schedule.last_run = timezone.now()
            schedule.next_run = self.calculate_next_run(schedule)
            schedule.save(update_fields=["last_run", "next_run"])
            
            # Link job to schedule
            job.schedule = schedule
            job.save(update_fields=["schedule"])
            
            return job
        except Exception as e:
            logger.error(f"Failed to create job from schedule {schedule.id}: {e}")
            return None

    def process_due_schedules(self) -> int:
        """Process all schedules that are due to run."""
        now = timezone.now()
        due_schedules = Schedule.objects.filter(
            enabled=True,
            next_run__lte=now
        ).select_related("customer", "created_by")
        
        count = 0
        for schedule in due_schedules:
            job = self.create_scheduled_job(schedule)
            if job:
                count += 1
                logger.info(f"Created job {job.id} from schedule {schedule.id} ({schedule.name})")
        
        return count


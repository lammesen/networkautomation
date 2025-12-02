"""Django signals for the jobs app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from webnet.jobs.models import Schedule
from webnet.jobs.schedule_service import ScheduleService


@receiver(post_save, sender=Schedule)
def update_schedule_next_run(sender, instance, created, **kwargs):
    """Update next_run when a schedule is created or updated."""
    # Only update if created or enabled, and avoid recursion
    if not kwargs.get("update_fields") or "next_run" not in kwargs.get("update_fields", []):
        if created or instance.enabled:
            ss = ScheduleService()
            next_run = ss.calculate_next_run(instance)
            if instance.next_run != next_run:
                # Use update() to avoid triggering signal again
                Schedule.objects.filter(pk=instance.pk).update(next_run=next_run)

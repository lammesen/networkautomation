"""Django signals for the jobs app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from webnet.jobs.models import Schedule
from webnet.jobs.schedule_service import ScheduleService


@receiver(post_save, sender=Schedule)
def update_schedule_next_run(sender, instance, created, **kwargs):
    """Update next_run when a schedule is created or updated."""
    if created or instance.enabled:
        ss = ScheduleService()
        # Avoid recursion by checking if next_run needs update
        next_run = ss.calculate_next_run(instance)
        if instance.next_run != next_run:
            instance.next_run = next_run
            instance.save(update_fields=["next_run"])

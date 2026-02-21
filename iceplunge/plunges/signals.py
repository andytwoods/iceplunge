import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from iceplunge.plunges.models import PlungeLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PlungeLog, dispatch_uid="plunge_log_schedule_reactive_prompts")
def on_plunge_log_created(sender, instance, created, **kwargs):
    """After a new plunge is logged, schedule two reactive cognitive prompts."""
    if not created:
        return
    try:
        from iceplunge.notifications.helpers.scheduling import schedule_reactive_prompts

        schedule_reactive_prompts(instance)
    except Exception:
        # Scheduling failure must never break the plunge-logging flow
        logger.exception("Failed to schedule reactive prompts for PlungeLog %s", instance.pk)

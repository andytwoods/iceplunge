"""
Huey background tasks for notifications.

Each function here is a thin wrapper: validate the input, delegate to a helper,
handle queue-specific concerns (retries, scheduling).
"""
import logging

from huey import crontab
from huey.contrib.djhuey import db_task
from huey.contrib.djhuey import periodic_task

from iceplunge.notifications.models import PromptEvent

logger = logging.getLogger(__name__)


@db_task(retries=2, retry_delay=60)
def send_prompt_task(prompt_event_id: int) -> None:
    """
    Send a push notification for the given PromptEvent.

    Sets PromptEvent.sent_at on success.
    """
    from django.utils import timezone

    from iceplunge.notifications.onesignal import OneSignalError
    from iceplunge.notifications.onesignal import send_push

    try:
        prompt = PromptEvent.objects.select_related("user").get(pk=prompt_event_id)
    except PromptEvent.DoesNotExist:
        logger.warning("send_prompt_task: PromptEvent %s not found", prompt_event_id)
        return

    try:
        send_push(
            user=prompt.user,
            title="Time for your cognitive assessment",
            body="Tap to start your session.",
            data={"prompt_event_id": prompt_event_id},
        )
        PromptEvent.objects.filter(pk=prompt_event_id).update(sent_at=timezone.now())
    except OneSignalError:
        logger.exception("send_prompt_task: OneSignal error for prompt %s", prompt_event_id)
        raise


@periodic_task(crontab(minute="*"))
def check_and_dispatch_due_prompts() -> None:
    """
    Runs every minute.
    Queries for unsent PromptEvents whose scheduled_at has passed and enqueues
    send_prompt_task for each.
    """
    from django.utils import timezone

    due = PromptEvent.objects.filter(sent_at__isnull=True, scheduled_at__lte=timezone.now())
    for prompt in due:
        send_prompt_task(prompt.pk)


@periodic_task(crontab(hour="0", minute="0"))
def dispatch_daily_prompts_task() -> None:
    """
    Runs once at midnight UTC.
    Iterates all users with push_enabled=True and pre-computes N jittered prompt
    times within their window, creating PromptEvent rows for pick-up by
    check_and_dispatch_due_prompts.
    """
    from django.utils import timezone

    from iceplunge.notifications.helpers.scheduling import schedule_daily_prompts_for_user
    from iceplunge.notifications.models import NotificationProfile

    today = timezone.now().date()
    profiles = NotificationProfile.objects.filter(push_enabled=True).select_related("user")
    for profile in profiles:
        schedule_daily_prompts_for_user(profile.user, today)

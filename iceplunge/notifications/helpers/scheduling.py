"""
Notification scheduling helpers.

All business logic for creating PromptEvent records and enforcing rate limits
lives here; the Huey tasks in notifications/tasks.py are thin wrappers.
"""
import datetime
import logging
import random
import zoneinfo

from django.conf import settings
from django.utils import timezone

from iceplunge.notifications.models import NotificationProfile
from iceplunge.notifications.models import PromptEvent

logger = logging.getLogger(__name__)

# Windows (in minutes) for reactive prompt delays after a plunge
_REACTIVE_WINDOW_1 = (15, 30)   # 15–30 min post-plunge
_REACTIVE_WINDOW_2 = (120, 180)  # 2–3 h post-plunge


def daily_prompt_count(user, date: datetime.date) -> int:
    """Return the number of PromptEvents scheduled for the given user on the given date."""
    start = datetime.datetime.combine(date, datetime.time.min, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(days=1)
    return PromptEvent.objects.filter(
        user=user,
        scheduled_at__gte=start,
        scheduled_at__lt=end,
    ).count()


def minutes_since_last_prompt(user) -> int | None:
    """
    Return how many minutes have elapsed since the most recently *sent* prompt,
    or None if no prompt has ever been sent.
    """
    last = (
        PromptEvent.objects.filter(user=user, sent_at__isnull=False)
        .order_by("-sent_at")
        .first()
    )
    if last is None:
        return None
    delta = timezone.now() - last.sent_at
    return int(delta.total_seconds() / 60)


def _can_schedule_prompt(user) -> bool:
    """Return True if adding a prompt now would not violate cap or gap rules."""
    today = timezone.now().date()
    cap = getattr(settings, "NOTIFICATIONS_DAILY_PROMPT_CAP", 4)
    if daily_prompt_count(user, today) >= cap:
        return False

    min_gap = getattr(settings, "NOTIFICATIONS_MIN_GAP_MINUTES", 45)
    minutes = minutes_since_last_prompt(user)
    if minutes is not None and minutes < min_gap:
        return False

    return True


def schedule_reactive_prompts(plunge_log) -> list[PromptEvent]:
    """
    Create two reactive PromptEvent records after a plunge is logged.

    Prompt 1: 15–30 min post-plunge.
    Prompt 2: 2–3 h post-plunge.

    Respects the daily cap and 45-minute gap rule; creates no records if the
    user has already hit the cap.

    Returns the list of PromptEvent objects created (may be empty or partial).
    """
    from iceplunge.notifications import tasks as notif_tasks  # avoid circular at module level

    user = plunge_log.user
    plunge_time = plunge_log.timestamp
    created = []

    for window_min, window_max in (_REACTIVE_WINDOW_1, _REACTIVE_WINDOW_2):
        if not _can_schedule_prompt(user):
            break
        delay_minutes = random.randint(window_min, window_max)
        scheduled_at = plunge_time + datetime.timedelta(minutes=delay_minutes)
        prompt = PromptEvent.objects.create(
            user=user,
            scheduled_at=scheduled_at,
            prompt_type=PromptEvent.PromptType.REACTIVE,
            linked_plunge=plunge_log,
        )
        created.append(prompt)
        notif_tasks.send_prompt_task.schedule((prompt.pk,), delay=delay_minutes * 60)

    return created


def should_send_scheduled_prompt(user, prompt_type: str) -> bool:
    """
    Return True if a scheduled prompt of the given type should be sent to the user.

    Checks:
    - push_enabled on NotificationProfile
    - Daily cap not exceeded
    - 45-minute gap since last sent prompt
    """
    try:
        profile = user.notification_profile
    except NotificationProfile.DoesNotExist:
        return False

    if not profile.push_enabled:
        return False

    return _can_schedule_prompt(user)


def schedule_daily_prompts_for_user(user, date: datetime.date) -> list[PromptEvent]:
    """
    Create morning and evening PromptEvent records for the given user and date.

    Uses the user's NotificationProfile time preferences. Falls back to UTC if
    no timezone is known.

    Returns the list of PromptEvent objects created.
    """
    from iceplunge.notifications import tasks as notif_tasks  # avoid circular

    try:
        profile = user.notification_profile
    except NotificationProfile.DoesNotExist:
        return []

    if not profile.push_enabled:
        return []

    created = []
    for prompt_type, window_time in (
        (PromptEvent.PromptType.SCHEDULED, profile.morning_window_start),
        (PromptEvent.PromptType.SCHEDULED, profile.evening_window_start),
    ):
        if not should_send_scheduled_prompt(user, prompt_type):
            break

        # Use UTC for scheduling (T6.3 acceptance test expects local time awareness)
        # The morning_window_start / evening_window_start are interpreted as local times.
        # Without a stored user timezone, we schedule in UTC.
        naive_dt = datetime.datetime.combine(date, window_time)
        scheduled_at = naive_dt.replace(tzinfo=datetime.timezone.utc)

        prompt = PromptEvent.objects.create(
            user=user,
            scheduled_at=scheduled_at,
            prompt_type=prompt_type,
        )
        created.append(prompt)
        notif_tasks.send_prompt_task.schedule((prompt.pk,), eta=scheduled_at)

    return created

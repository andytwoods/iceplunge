"""
Anti-gaming voluntary session rate limits.

Limits are configurable via Django settings so they can be adjusted without
code changes.
"""
import datetime

from django.conf import settings
from django.utils import timezone


# Defaults — overridable via settings
MAX_VOLUNTARY_SESSIONS_PER_HOUR: int = getattr(settings, "MAX_VOLUNTARY_SESSIONS_PER_HOUR", 2)
MAX_VOLUNTARY_SESSIONS_PER_DAY: int = getattr(settings, "MAX_VOLUNTARY_SESSIONS_PER_DAY", 8)


def check_voluntary_rate_limit(user) -> tuple[bool, str | None]:
    """
    Check whether the user is allowed to start another voluntary session.

    Returns:
        (True, None)         — allowed
        (False, reason_str)  — blocked; reason_str is a human-readable explanation.
    """
    from iceplunge.tasks.models import CognitiveSession

    now = timezone.now()

    # Per-hour limit
    hour_ago = now - datetime.timedelta(hours=1)
    hourly_count = CognitiveSession.objects.filter(
        user=user,
        is_practice=False,
        started_at__gte=hour_ago,
    ).count()
    if hourly_count >= MAX_VOLUNTARY_SESSIONS_PER_HOUR:
        return (
            False,
            (
                f"You have started {MAX_VOLUNTARY_SESSIONS_PER_HOUR} sessions in the last hour. "
                "Please wait a while before starting another."
            ),
        )

    # Per-day limit
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = CognitiveSession.objects.filter(
        user=user,
        is_practice=False,
        started_at__gte=day_start,
    ).count()
    if daily_count >= MAX_VOLUNTARY_SESSIONS_PER_DAY:
        return (
            False,
            (
                f"You have reached the maximum of {MAX_VOLUNTARY_SESSIONS_PER_DAY} sessions "
                "for today. Come back tomorrow!"
            ),
        )

    return True, None

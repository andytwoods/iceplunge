"""Helper functions for determining whether a user needs to submit covariate data."""

import datetime

from .models import DailyCovariate
from .models import WeeklyCovariate


def needs_daily_covariate(user, today: datetime.date | None = None) -> bool:
    """Return True if *user* has no DailyCovariate record for *today* (defaults to current date)."""
    if today is None:
        today = datetime.date.today()
    return not DailyCovariate.objects.filter(user=user, date=today).exists()


def needs_weekly_covariate(user, today: datetime.date | None = None) -> bool:
    """Return True if *user* has no WeeklyCovariate record for the current ISO week (Monday-anchored)."""
    if today is None:
        today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    return not WeeklyCovariate.objects.filter(user=user, week_start=week_start).exists()

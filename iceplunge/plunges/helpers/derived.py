"""Pure functions for computing plunge-relative derived variables.

No Django ORM calls are made here — all inputs are plain Python objects so
these functions can be tested without a database.
"""

from __future__ import annotations

import datetime
from typing import Sequence


def time_since_last_plunge(
    plunge_logs: Sequence,
    session_dt: datetime.datetime,
) -> datetime.timedelta | None:
    """Return the timedelta between the most-recent plunge before *session_dt* and *session_dt*.

    Returns ``None`` if there are no plunges before *session_dt*.
    Each element of *plunge_logs* must have a ``timestamp`` attribute.
    """
    prior = [p for p in plunge_logs if p.timestamp < session_dt]
    if not prior:
        return None
    latest = max(prior, key=lambda p: p.timestamp)
    return session_dt - latest.timestamp


def proximity_bin(delta: datetime.timedelta | None) -> str:
    """Classify *delta* into a named proximity bin.

    Returns one of: ``"no_plunge"``, ``"pre"``, ``"0-15m"``,
    ``"15-60m"``, ``"1-3h"``, ``">3h"``.

    ``"pre"`` is reserved for a negative delta (session occurs *before* a plunge).
    """
    if delta is None:
        return "no_plunge"
    total_seconds = delta.total_seconds()
    if total_seconds < 0:
        return "pre"
    minutes = total_seconds / 60
    if minutes <= 15:
        return "0-15m"
    if minutes <= 60:
        return "15-60m"
    hours = minutes / 60
    if hours <= 3:
        return "1-3h"
    return ">3h"


def same_day_plunge_count(
    plunge_logs: Sequence,
    session_date: datetime.date,
) -> int:
    """Return the number of plunges whose date matches *session_date*."""
    return sum(
        1 for p in plunge_logs
        if p.timestamp.date() == session_date
    )


def rolling_frequency(
    plunge_logs: Sequence,
    session_dt: datetime.datetime,
    days: int,
) -> float:
    """Return plunges per day within the *days*-day window ending at *session_dt*.

    A plunge is included if its timestamp falls within
    ``(session_dt - timedelta(days=days), session_dt]``.
    """
    if days <= 0:
        return 0.0
    window_start = session_dt - datetime.timedelta(days=days)
    count = sum(
        1 for p in plunge_logs
        if window_start < p.timestamp <= session_dt
    )
    return count / days


def season(dt: datetime.datetime | datetime.date) -> str:
    """Return the northern-hemisphere meteorological season for *dt*.

    Returns one of: ``"spring"``, ``"summer"``, ``"autumn"``, ``"winter"``.
    """
    month = dt.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"

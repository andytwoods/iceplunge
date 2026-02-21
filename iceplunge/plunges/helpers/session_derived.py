"""Compute the full set of derived session variables for a given user and session datetime.

This module is the only place that touches the ORM for derived-variable logic;
it calls the pure functions in :mod:`derived` with the results.
"""

from __future__ import annotations

import datetime

from iceplunge.plunges.helpers.derived import proximity_bin
from iceplunge.plunges.helpers.derived import rolling_frequency
from iceplunge.plunges.helpers.derived import same_day_plunge_count
from iceplunge.plunges.helpers.derived import season
from iceplunge.plunges.helpers.derived import time_since_last_plunge


def compute_session_derived(user, session_dt: datetime.datetime) -> dict:
    """Return a dict of derived variable values for *user* at *session_dt*.

    Queries the DB to fetch the user's plunge history, then delegates to
    the pure functions in :mod:`derived`.
    """
    from iceplunge.plunges.models import PlungeLog  # local import avoids circular deps

    plunge_logs = list(
        PlungeLog.objects.filter(user=user, timestamp__lt=session_dt)
        .order_by("timestamp")
        .only("timestamp")
    )

    delta = time_since_last_plunge(plunge_logs, session_dt)

    return {
        "time_since_last_plunge_seconds": delta.total_seconds() if delta is not None else None,
        "proximity_bin": proximity_bin(delta),
        "same_day_plunge_count": same_day_plunge_count(plunge_logs, session_dt.date()),
        "rolling_frequency_7d": rolling_frequency(plunge_logs, session_dt, days=7),
        "rolling_frequency_28d": rolling_frequency(plunge_logs, session_dt, days=28),
        "season": season(session_dt),
    }

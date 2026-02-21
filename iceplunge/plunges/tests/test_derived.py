"""Tests for the pure derived-variable functions."""

import datetime
from types import SimpleNamespace

import pytest

from iceplunge.plunges.helpers.derived import proximity_bin
from iceplunge.plunges.helpers.derived import rolling_frequency
from iceplunge.plunges.helpers.derived import same_day_plunge_count
from iceplunge.plunges.helpers.derived import season
from iceplunge.plunges.helpers.derived import time_since_last_plunge


def _log(dt_str):
    """Return a mock plunge log with the given ISO timestamp string."""
    dt = datetime.datetime.fromisoformat(dt_str).replace(tzinfo=datetime.timezone.utc)
    return SimpleNamespace(timestamp=dt)


SESSION_DT = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


class TestTimeSinceLastPlunge:
    def test_no_plunges_returns_none(self):
        assert time_since_last_plunge([], SESSION_DT) is None

    def test_plunge_before_session(self):
        logs = [_log("2024-06-15T11:00:00")]
        delta = time_since_last_plunge(logs, SESSION_DT)
        assert delta == datetime.timedelta(hours=1)

    def test_only_counts_prior_plunges(self):
        logs = [_log("2024-06-15T13:00:00")]  # after session
        assert time_since_last_plunge(logs, SESSION_DT) is None

    def test_picks_most_recent_prior(self):
        logs = [_log("2024-06-15T10:00:00"), _log("2024-06-15T11:30:00")]
        delta = time_since_last_plunge(logs, SESSION_DT)
        assert delta == datetime.timedelta(minutes=30)

    def test_plunge_yesterday(self):
        logs = [_log("2024-06-14T12:00:00")]
        delta = time_since_last_plunge(logs, SESSION_DT)
        assert delta == datetime.timedelta(days=1)


class TestProximityBin:
    def test_no_plunge(self):
        assert proximity_bin(None) == "no_plunge"

    def test_10_minutes(self):
        assert proximity_bin(datetime.timedelta(minutes=10)) == "0-15m"

    def test_exactly_15_minutes(self):
        assert proximity_bin(datetime.timedelta(minutes=15)) == "0-15m"

    def test_30_minutes(self):
        assert proximity_bin(datetime.timedelta(minutes=30)) == "15-60m"

    def test_2_hours(self):
        assert proximity_bin(datetime.timedelta(hours=2)) == "1-3h"

    def test_4_hours(self):
        assert proximity_bin(datetime.timedelta(hours=4)) == ">3h"

    def test_negative_delta_is_pre(self):
        assert proximity_bin(datetime.timedelta(minutes=-5)) == "pre"

    def test_5_minutes_ago_is_0_15m(self):
        assert proximity_bin(datetime.timedelta(minutes=5)) == "0-15m"


class TestSameDayPlungeCount:
    def test_no_plunges(self):
        assert same_day_plunge_count([], SESSION_DT.date()) == 0

    def test_one_same_day(self):
        logs = [_log("2024-06-15T09:00:00")]
        assert same_day_plunge_count(logs, SESSION_DT.date()) == 1

    def test_different_day_not_counted(self):
        logs = [_log("2024-06-14T09:00:00")]
        assert same_day_plunge_count(logs, SESSION_DT.date()) == 0

    def test_multiple_same_day(self):
        logs = [_log("2024-06-15T08:00:00"), _log("2024-06-15T16:00:00")]
        assert same_day_plunge_count(logs, SESSION_DT.date()) == 2


class TestRollingFrequency:
    def test_no_plunges(self):
        assert rolling_frequency([], SESSION_DT, days=7) == 0.0

    def test_one_plunge_in_7_days(self):
        logs = [_log("2024-06-12T10:00:00")]
        assert rolling_frequency(logs, SESSION_DT, days=7) == pytest.approx(1 / 7)

    def test_plunge_outside_window_not_counted(self):
        logs = [_log("2024-06-01T10:00:00")]  # > 7 days ago
        assert rolling_frequency(logs, SESSION_DT, days=7) == 0.0

    def test_zero_days_returns_zero(self):
        logs = [_log("2024-06-15T10:00:00")]
        assert rolling_frequency(logs, SESSION_DT, days=0) == 0.0


class TestSeason:
    def test_spring(self):
        assert season(datetime.date(2024, 4, 1)) == "spring"

    def test_summer(self):
        assert season(datetime.date(2024, 7, 1)) == "summer"

    def test_autumn(self):
        assert season(datetime.date(2024, 10, 1)) == "autumn"

    def test_winter_january(self):
        assert season(datetime.date(2024, 1, 1)) == "winter"

    def test_winter_december(self):
        assert season(datetime.date(2024, 12, 31)) == "winter"

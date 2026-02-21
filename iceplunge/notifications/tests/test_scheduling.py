"""Tests for notification scheduling helpers."""
import datetime

import pytest
from django.utils import timezone

from iceplunge.notifications.helpers.scheduling import (
    daily_prompt_count,
    minutes_since_last_prompt,
    schedule_daily_prompts_for_user,
    schedule_reactive_prompts,
    should_send_scheduled_prompt,
)
from iceplunge.notifications.models import NotificationProfile, PromptEvent
from iceplunge.plunges.models import PlungeLog
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _make_plunge(user, timestamp=None):
    return PlungeLog.objects.create(
        user=user,
        timestamp=timestamp or timezone.now(),
        duration_minutes=5,
        immersion_depth="chest",
        context="bath",
        perceived_intensity=3,
    )


def _make_profile(user, push_enabled=True):
    profile, _ = NotificationProfile.objects.get_or_create(user=user)
    profile.push_enabled = push_enabled
    profile.save()
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# daily_prompt_count
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDailyPromptCount:
    def test_zero_when_no_prompts(self):
        user = _consented_user()
        assert daily_prompt_count(user, timezone.now().date()) == 0

    def test_counts_prompts_on_given_date(self):
        user = _consented_user()
        today = timezone.now().date()
        today_dt = datetime.datetime.combine(today, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
        PromptEvent.objects.create(
            user=user,
            scheduled_at=today_dt,
            prompt_type=PromptEvent.PromptType.SCHEDULED,
        )
        assert daily_prompt_count(user, today) == 1

    def test_ignores_prompts_from_other_days(self):
        user = _consented_user()
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        yesterday_dt = datetime.datetime.combine(yesterday, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
        PromptEvent.objects.create(
            user=user,
            scheduled_at=yesterday_dt,
            prompt_type=PromptEvent.PromptType.SCHEDULED,
        )
        assert daily_prompt_count(user, timezone.now().date()) == 0


# ─────────────────────────────────────────────────────────────────────────────
# minutes_since_last_prompt
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMinutesSinceLastPrompt:
    def test_none_when_no_prompts_sent(self):
        user = _consented_user()
        assert minutes_since_last_prompt(user) is None

    def test_returns_minutes_elapsed(self):
        user = _consented_user()
        sent_at = timezone.now() - datetime.timedelta(minutes=30)
        PromptEvent.objects.create(
            user=user,
            scheduled_at=sent_at,
            sent_at=sent_at,
            prompt_type=PromptEvent.PromptType.REACTIVE,
        )
        minutes = minutes_since_last_prompt(user)
        assert 28 <= minutes <= 32  # allow small timing tolerance


# ─────────────────────────────────────────────────────────────────────────────
# schedule_reactive_prompts
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestScheduleReactivePrompts:
    # MemoryHuey with immediate=False for .schedule() calls — tasks queue but don't execute
    # so no HTTP calls are made during tests.

    def test_creates_two_prompts_when_cap_allows(self):
        user = _consented_user()
        _make_profile(user)
        plunge = _make_plunge(user)
        events = schedule_reactive_prompts(plunge)
        assert len(events) == 2
        assert all(e.prompt_type == PromptEvent.PromptType.REACTIVE for e in events)
        assert all(e.linked_plunge == plunge for e in events)

    def test_first_prompt_within_15_to_30_min(self):
        user = _consented_user()
        _make_profile(user)
        plunge = _make_plunge(user)
        events = schedule_reactive_prompts(plunge)
        delta_min = (events[0].scheduled_at - plunge.timestamp).total_seconds() / 60
        assert 15 <= delta_min <= 30

    def test_second_prompt_within_2_to_3_hours(self):
        user = _consented_user()
        _make_profile(user)
        plunge = _make_plunge(user)
        events = schedule_reactive_prompts(plunge)
        delta_min = (events[1].scheduled_at - plunge.timestamp).total_seconds() / 60
        assert 120 <= delta_min <= 180

    def test_no_prompts_created_at_daily_cap(self):
        user = _consented_user()
        _make_profile(user)
        plunge = _make_plunge(user)
        today = timezone.now().date()
        # Fill up the daily cap (default = 4)
        for i in range(4):
            cap_dt = datetime.datetime.combine(
                today, datetime.time(9 + i, 0), tzinfo=datetime.timezone.utc
            )
            PromptEvent.objects.create(
                user=user,
                scheduled_at=cap_dt,
                prompt_type=PromptEvent.PromptType.SCHEDULED,
            )
        events = schedule_reactive_prompts(plunge)
        assert len(events) == 0


# ─────────────────────────────────────────────────────────────────────────────
# should_send_scheduled_prompt
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestShouldSendScheduledPrompt:
    def test_returns_false_without_profile(self):
        user = _consented_user()
        assert should_send_scheduled_prompt(user, "scheduled") is False

    def test_returns_false_when_push_disabled(self):
        user = _consented_user()
        _make_profile(user, push_enabled=False)
        assert should_send_scheduled_prompt(user, "scheduled") is False

    def test_returns_true_when_push_enabled_and_no_cap(self):
        user = _consented_user()
        _make_profile(user, push_enabled=True)
        assert should_send_scheduled_prompt(user, "scheduled") is True


# ─────────────────────────────────────────────────────────────────────────────
# schedule_daily_prompts_for_user
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestScheduleDailyPromptsForUser:
    def test_does_not_create_prompts_when_push_disabled(self):
        user = _consented_user()
        _make_profile(user, push_enabled=False)
        events = schedule_daily_prompts_for_user(user, timezone.now().date())
        assert events == []
        assert PromptEvent.objects.filter(user=user).count() == 0

    def test_creates_two_prompts_when_push_enabled(self):
        user = _consented_user()
        _make_profile(user, push_enabled=True)
        today = timezone.now().date()
        events = schedule_daily_prompts_for_user(user, today)
        assert len(events) == 2

    def test_morning_prompt_scheduled_at_morning_window(self):
        user = _consented_user()
        profile = _make_profile(user, push_enabled=True)
        profile.morning_window_start = datetime.time(8, 0)
        profile.save()
        today = timezone.now().date()
        events = schedule_daily_prompts_for_user(user, today)
        morning_prompt = events[0]
        assert morning_prompt.scheduled_at.hour == 8
        assert morning_prompt.scheduled_at.minute == 0

    def test_no_prompts_without_profile(self):
        user = _consented_user()
        events = schedule_daily_prompts_for_user(user, timezone.now().date())
        assert events == []

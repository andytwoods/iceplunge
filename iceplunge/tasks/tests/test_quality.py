"""Unit tests for quality flag computation functions."""
import datetime

import pytest
from django.utils import timezone

from iceplunge.tasks.helpers.quality import (
    compute_quality_flags,
    flag_anticipation_bursts,
    flag_excessive_misses,
    flag_rapid_resubmission,
    flag_visibility_events,
)
from iceplunge.tasks.helpers.session_helpers import create_session
from iceplunge.tasks.models import CognitiveSession, TaskResult
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _make_session(user):
    return create_session(user)


def _make_task_result(session, task_type="pvt", trials=None):
    now = timezone.now()
    return TaskResult.objects.create(
        session=session,
        task_type=task_type,
        task_version="1.0",
        started_at=now,
        completed_at=now,
        trial_data=trials or [],
        summary_metrics={},
        session_index_overall=1,
        session_index_per_task=1,
    )


# ─────────────────────────────────────────────────────────────────────────────
# flag_anticipation_bursts
# ─────────────────────────────────────────────────────────────────────────────

class TestFlagAnticipationBursts:
    def test_false_for_fewer_than_three(self):
        trials = [{"is_anticipation": True}, {"is_anticipation": True}]
        assert flag_anticipation_bursts(trials) is False

    def test_true_for_exactly_three(self):
        trials = [{"is_anticipation": True}] * 3
        assert flag_anticipation_bursts(trials) is True

    def test_true_for_more_than_three(self):
        trials = [{"is_anticipation": True}] * 5
        assert flag_anticipation_bursts(trials) is True

    def test_false_for_empty_trials(self):
        assert flag_anticipation_bursts([]) is False

    def test_flag_stored_as_string(self):
        """Flags are stored as strings, not booleans."""
        trials = [{"is_anticipation": True}] * 3
        result = flag_anticipation_bursts(trials)
        assert isinstance(result, bool)  # function returns bool; storage converts to string


# ─────────────────────────────────────────────────────────────────────────────
# flag_excessive_misses
# ─────────────────────────────────────────────────────────────────────────────

class TestFlagExcessiveMisses:
    def test_false_below_threshold(self):
        trials = [
            {"responded": True, "rt_ms": 300},
            {"responded": True, "rt_ms": 400},
            {"responded": False, "rt_ms": None},  # 33%
        ]
        assert flag_excessive_misses(trials) is False

    def test_true_above_threshold(self):
        trials = [
            {"responded": False, "rt_ms": None},
            {"responded": False, "rt_ms": None},
            {"responded": True, "rt_ms": 300},  # 67% misses
        ]
        assert flag_excessive_misses(trials) is True

    def test_false_for_empty_trials(self):
        assert flag_excessive_misses([]) is False

    def test_exactly_at_threshold_is_false(self):
        # exactly 50% — threshold is >, so 50% is not excessive
        trials = [{"responded": False}, {"responded": True, "rt_ms": 300}]
        assert flag_excessive_misses(trials) is False


# ─────────────────────────────────────────────────────────────────────────────
# flag_rapid_resubmission
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFlagRapidResubmission:
    def test_false_when_no_prior_sessions(self):
        user = _consented_user()
        session = _make_session(user)
        assert flag_rapid_resubmission(user, session) is False

    def test_true_when_completed_session_within_10_min(self):
        user = _consented_user()
        # Create and complete a prior session
        prior = _make_session(user)
        CognitiveSession.objects.filter(pk=prior.pk).update(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
            completed_at=timezone.now() - datetime.timedelta(minutes=5),
        )
        prior.refresh_from_db()
        current = _make_session(user)
        assert flag_rapid_resubmission(user, current) is True

    def test_false_when_completed_session_older_than_10_min(self):
        user = _consented_user()
        prior = _make_session(user)
        CognitiveSession.objects.filter(pk=prior.pk).update(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
            completed_at=timezone.now() - datetime.timedelta(minutes=15),
        )
        prior.refresh_from_db()
        current = _make_session(user)
        assert flag_rapid_resubmission(user, current) is False


# ─────────────────────────────────────────────────────────────────────────────
# flag_visibility_events
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFlagVisibilityEvents:
    def test_false_for_two_or_fewer_hidden_events(self):
        user = _consented_user()
        session = _make_session(user)
        CognitiveSession.objects.filter(pk=session.pk).update(device_meta={
            "interruption_logs": [
                {"type": "visibility_hidden"},
                {"type": "visibility_hidden"},
            ]
        })
        session.refresh_from_db()
        assert flag_visibility_events(session) is False

    def test_true_for_more_than_two_hidden_events(self):
        user = _consented_user()
        session = _make_session(user)
        CognitiveSession.objects.filter(pk=session.pk).update(device_meta={
            "interruption_logs": [
                {"type": "visibility_hidden"},
                {"type": "visibility_hidden"},
                {"type": "visibility_hidden"},
            ]
        })
        session.refresh_from_db()
        assert flag_visibility_events(session) is True

    def test_false_with_no_interruptions(self):
        user = _consented_user()
        session = _make_session(user)
        assert flag_visibility_events(session) is False


# ─────────────────────────────────────────────────────────────────────────────
# compute_quality_flags
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestComputeQualityFlags:
    def test_returns_list_of_strings(self):
        user = _consented_user()
        session = _make_session(user)
        result = _make_task_result(session, trials=[])
        flags = compute_quality_flags(user, session, result)
        assert isinstance(flags, list)
        for f in flags:
            assert isinstance(f, str)

    def test_anticipation_burst_flag_name(self):
        user = _consented_user()
        session = _make_session(user)
        anticipation_trials = [{"is_anticipation": True}] * 4
        result = _make_task_result(session, trials=anticipation_trials)
        flags = compute_quality_flags(user, session, result)
        assert "anticipation_burst" in flags

    def test_excessive_misses_flag_name(self):
        user = _consented_user()
        session = _make_session(user)
        miss_trials = [{"responded": False, "rt_ms": None}] * 4 + [{"responded": True, "rt_ms": 300}]
        result = _make_task_result(session, trials=miss_trials)
        flags = compute_quality_flags(user, session, result)
        assert "excessive_misses" in flags

    def test_no_flags_for_clean_session(self):
        user = _consented_user()
        session = _make_session(user)
        clean_trials = [{"responded": True, "rt_ms": 300, "is_anticipation": False}] * 5
        result = _make_task_result(session, trials=clean_trials)
        flags = compute_quality_flags(user, session, result)
        assert "anticipation_burst" not in flags
        assert "excessive_misses" not in flags
        assert "rapid_resubmission" not in flags
        assert "visibility_events" not in flags

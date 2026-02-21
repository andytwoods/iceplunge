"""Unit and view tests for voluntary session rate limiting."""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.tasks.helpers.rate_limits import check_voluntary_rate_limit
from iceplunge.tasks.models import CognitiveSession
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _create_session(user, *, started_at=None, is_practice=False, complete=False):
    """Helper to create a CognitiveSession, optionally marking it complete."""
    now = started_at or timezone.now()
    session = CognitiveSession.objects.create(
        user=user,
        is_practice=is_practice,
        started_at=now,
        task_order=["pvt"],
        random_seed="test",
        completion_status=(
            CognitiveSession.CompletionStatus.COMPLETE
            if complete
            else CognitiveSession.CompletionStatus.IN_PROGRESS
        ),
        completed_at=now if complete else None,
    )
    return session


# ─────────────────────────────────────────────────────────────────────────────
# check_voluntary_rate_limit — unit tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckVoluntaryRateLimit:
    def test_allowed_when_no_sessions(self):
        user = _consented_user()
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is True
        assert reason is None

    def test_allowed_with_one_session_this_hour(self):
        user = _consented_user()
        _create_session(user)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is True

    def test_blocked_at_hourly_limit(self):
        """Third voluntary session within one hour is blocked."""
        user = _consented_user()
        _create_session(user)
        _create_session(user)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is False
        assert reason is not None
        assert "hour" in reason.lower()

    def test_practice_sessions_do_not_count_toward_limit(self):
        user = _consented_user()
        _create_session(user, is_practice=True)
        _create_session(user, is_practice=True)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is True

    def test_old_sessions_do_not_count_toward_hourly_limit(self):
        user = _consented_user()
        two_hours_ago = timezone.now() - datetime.timedelta(hours=2)
        _create_session(user, started_at=two_hours_ago)
        _create_session(user, started_at=two_hours_ago)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is True

    def test_blocked_at_daily_limit(self, monkeypatch):
        """After 8 sessions today the user is blocked for the rest of the day."""
        import iceplunge.tasks.helpers.rate_limits as rl

        monkeypatch.setattr(rl, "MAX_VOLUNTARY_SESSIONS_PER_HOUR", 100)  # bypass hourly limit
        monkeypatch.setattr(rl, "MAX_VOLUNTARY_SESSIONS_PER_DAY", 8)
        user = _consented_user()
        for _ in range(8):
            _create_session(user)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is False
        assert reason is not None
        assert "today" in reason.lower() or "maximum" in reason.lower()

    def test_reason_mentions_count(self):
        user = _consented_user()
        _create_session(user)
        _create_session(user)
        allowed, reason = check_voluntary_rate_limit(user)
        assert allowed is False
        assert "2" in reason  # mentions MAX_VOLUNTARY_SESSIONS_PER_HOUR (2)


# ─────────────────────────────────────────────────────────────────────────────
# SessionStartView — rate limit view integration tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionStartViewRateLimit:
    def _url(self):
        return reverse("tasks:start")

    def test_get_returns_200_when_allowed(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        assert response.status_code == 200

    def test_get_returns_429_when_rate_limited(self, client):
        user = _consented_user()
        client.force_login(user)
        _create_session(user)
        _create_session(user)
        response = client.get(self._url())
        assert response.status_code == 429

    def test_429_renders_rate_limit_template(self, client):
        user = _consented_user()
        client.force_login(user)
        _create_session(user)
        _create_session(user)
        response = client.get(self._url())
        assert b"Too many sessions" in response.content or b"sessions" in response.content

    def test_post_returns_429_when_rate_limited(self, client):
        user = _consented_user()
        client.force_login(user)
        _create_session(user)
        _create_session(user)
        response = client.post(self._url(), {})
        assert response.status_code == 429

    def test_post_succeeds_when_within_limit(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(self._url(), {})
        # Either 200 (invalid form re-render) or 302 (redirect) — not 429
        assert response.status_code != 429

    def test_reason_appears_in_rate_limited_response(self, client):
        user = _consented_user()
        client.force_login(user)
        _create_session(user)
        _create_session(user)
        response = client.get(self._url())
        assert response.status_code == 429
        # The reason text should appear somewhere in the rendered HTML
        assert b"Please wait" in response.content or b"hour" in response.content.lower()

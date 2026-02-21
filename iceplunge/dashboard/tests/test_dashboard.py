"""Tests for the participant dashboard views."""
import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.tasks.helpers.session_helpers import create_session
from iceplunge.tasks.models import CognitiveSession, MoodRating, TaskResult
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _complete_session(user):
    session = create_session(user)
    CognitiveSession.objects.filter(pk=session.pk).update(
        completion_status=CognitiveSession.CompletionStatus.COMPLETE,
        completed_at=timezone.now(),
    )
    session.refresh_from_db()
    return session


def _pvt_result(session, median_rt=320, lapse_count=2):
    now = timezone.now()
    return TaskResult.objects.create(
        session=session,
        task_type="pvt",
        task_version="1.0",
        started_at=now,
        completed_at=now,
        trial_data=[],
        summary_metrics={"median_rt": median_rt, "lapse_count": lapse_count},
        session_index_overall=1,
        session_index_per_task=1,
        is_partial=False,
    )


def _mood_rating(session, valence=3, arousal=3, stress=2, sharpness=4):
    return MoodRating.objects.create(
        session=session, valence=valence, arousal=arousal, stress=stress, sharpness=sharpness
    )


# ─────────────────────────────────────────────────────────────────────────────
# DashboardView
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDashboardView:
    def _url(self):
        return reverse("dashboard:home")

    def test_requires_login(self, client):
        response = client.get(self._url())
        assert response.status_code == 302
        assert "/accounts/" in response["Location"]

    def test_renders_200_for_logged_in_user(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        assert response.status_code == 200

    def test_shows_empty_state_when_no_sessions(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        assert b"first cognitive session" in response.content

    def test_shows_session_count(self, client):
        user = _consented_user()
        client.force_login(user)
        _complete_session(user)
        response = client.get(self._url())
        assert response.status_code == 200
        assert b"1" in response.content


# ─────────────────────────────────────────────────────────────────────────────
# ChartDataView
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestChartDataView:
    def _url(self):
        return reverse("dashboard:chart_data")

    def test_requires_login(self, client):
        response = client.get(self._url())
        assert response.status_code == 302

    def test_returns_json_200(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        assert response.status_code == 200
        data = response.json()
        assert "rt_trend" in data
        assert "mood_trend" in data

    def test_rt_trend_empty_without_data(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        data = response.json()
        assert data["rt_trend"] == []

    def test_rt_trend_contains_pvt_metrics(self, client):
        user = _consented_user()
        client.force_login(user)
        session = _complete_session(user)
        _pvt_result(session, median_rt=340, lapse_count=3)
        response = client.get(self._url())
        data = response.json()
        assert len(data["rt_trend"]) == 1
        point = data["rt_trend"][0]
        assert point["median_rt"] == 340
        assert point["lapse_count"] == 3
        assert "date" in point

    def test_rt_trend_excludes_partial_results(self, client):
        user = _consented_user()
        client.force_login(user)
        session = _complete_session(user)
        now = timezone.now()
        TaskResult.objects.create(
            session=session,
            task_type="pvt",
            task_version="1.0",
            started_at=now,
            completed_at=now,
            trial_data=[],
            summary_metrics={"median_rt": 350, "lapse_count": 1},
            session_index_overall=1,
            session_index_per_task=1,
            is_partial=True,
        )
        response = client.get(self._url())
        data = response.json()
        assert data["rt_trend"] == []

    def test_mood_trend_contains_mood_ratings(self, client):
        user = _consented_user()
        client.force_login(user)
        session = _complete_session(user)
        _mood_rating(session, valence=4, arousal=3, stress=1, sharpness=5)
        response = client.get(self._url())
        data = response.json()
        assert len(data["mood_trend"]) == 1
        mood = data["mood_trend"][0]
        assert mood["valence"] == 4
        assert mood["arousal"] == 3
        assert mood["stress"] == 1
        assert mood["sharpness"] == 5

    def test_data_scoped_to_requesting_user(self, client):
        user_a = _consented_user()
        user_b = _consented_user()
        client.force_login(user_a)
        session_b = _complete_session(user_b)
        _pvt_result(session_b, median_rt=400, lapse_count=5)
        response = client.get(self._url())
        data = response.json()
        assert data["rt_trend"] == []

    def test_multiple_sessions_ordered_by_date(self, client):
        user = _consented_user()
        client.force_login(user)
        s1 = _complete_session(user)
        s2 = _complete_session(user)
        _pvt_result(s1, median_rt=300, lapse_count=1)
        _pvt_result(s2, median_rt=320, lapse_count=2)
        response = client.get(self._url())
        data = response.json()
        assert len(data["rt_trend"]) == 2

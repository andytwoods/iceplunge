import json
from uuid import uuid4

import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.tasks.helpers.session_helpers import create_session
from iceplunge.tasks.models import CognitiveSession, TaskResult
from iceplunge.tasks.registry import TASK_REGISTRY
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _make_session(user, status=CognitiveSession.CompletionStatus.IN_PROGRESS):
    session = create_session(user)
    if status != CognitiveSession.CompletionStatus.IN_PROGRESS:
        CognitiveSession.objects.filter(pk=session.pk).update(completion_status=status)
        session.refresh_from_db()
    return session


def _valid_payload(session, task_type=None, **overrides):
    if task_type is None:
        task_type = session.task_order[0]
    now_iso = timezone.now().isoformat()
    payload = {
        "session_id": str(session.id),
        "task_type": task_type,
        "task_version": "1.0",
        "started_at": now_iso,
        "ended_at": now_iso,
        "duration_ms": 60_000,
        "input_modality": "touch",
        "trials": [],
        "summary": {},
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# SessionStartView
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionStartView:
    def test_login_required(self, client):
        response = client.get(reverse("tasks:start"))
        assert response.status_code == 302

    def test_get_creates_session_and_shows_form(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("tasks:start"))
        assert response.status_code == 200
        assert CognitiveSession.objects.filter(user=user).exists()

    def test_get_reuses_in_progress_session(self, client):
        user = _consented_user()
        client.force_login(user)
        client.get(reverse("tasks:start"))
        count_after_first = CognitiveSession.objects.filter(user=user).count()
        client.get(reverse("tasks:start"))
        count_after_second = CognitiveSession.objects.filter(user=user).count()
        assert count_after_first == count_after_second

    def test_post_saves_covariate_and_redirects(self, client):
        user = _consented_user()
        client.force_login(user)
        client.get(reverse("tasks:start"))  # creates session
        data = {
            "caffeine_since_last_session": False,
            "minutes_since_last_meal": 60,
            "cold_hands": False,
            "wet_hands": False,
        }
        response = client.post(reverse("tasks:start"), data=data)
        assert response.status_code == 302
        assert "task" in response["Location"]

    def test_get_redirects_to_task_if_covariate_already_saved(self, client):
        from iceplunge.covariates.models import SessionCovariate

        user = _consented_user()
        client.force_login(user)
        client.get(reverse("tasks:start"))  # creates session, stored in Django session

        session = CognitiveSession.objects.get(user=user)
        SessionCovariate.objects.create(
            session=session,
            caffeine_since_last_session=False,
            cold_hands=False,
            wet_hands=False,
        )
        response = client.get(reverse("tasks:start"))
        assert response.status_code == 302
        assert "task" in response["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# SessionTaskView
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionTaskView:
    def test_login_required(self, client):
        session_id = uuid4()
        response = client.get(reverse("tasks:task", kwargs={"session_id": session_id}))
        assert response.status_code == 302

    def test_404_for_wrong_user(self, client):
        user1 = _consented_user()
        user2 = _consented_user()
        session = _make_session(user1)
        client.force_login(user2)
        response = client.get(reverse("tasks:task", kwargs={"session_id": session.id}))
        assert response.status_code == 404

    def test_shows_task_page(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        response = client.get(reverse("tasks:task", kwargs={"session_id": session.id}))
        assert response.status_code == 200
        assert response.context["task_type"] in TASK_REGISTRY

    def test_redirects_to_complete_when_all_done(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        now = timezone.now()
        for task_type in session.task_order:
            TaskResult.objects.create(
                session=session,
                task_type=task_type,
                task_version="1.0",
                started_at=now,
                completed_at=now,
                trial_data=[],
                summary_metrics={},
                session_index_overall=1,
                session_index_per_task=1,
            )
        response = client.get(reverse("tasks:task", kwargs={"session_id": session.id}))
        assert response.status_code == 302
        assert "complete" in response["Location"]


# ─────────────────────────────────────────────────────────────────────────────
# SessionCompleteView
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionCompleteView:
    def test_marks_session_complete(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        response = client.get(reverse("tasks:complete", kwargs={"session_id": session.id}))
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.completion_status == CognitiveSession.CompletionStatus.COMPLETE

    def test_completed_at_is_set(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        client.get(reverse("tasks:complete", kwargs={"session_id": session.id}))
        session.refresh_from_db()
        assert session.completed_at is not None

    def test_404_for_wrong_user(self, client):
        user1 = _consented_user()
        user2 = _consented_user()
        session = _make_session(user1)
        client.force_login(user2)
        response = client.get(reverse("tasks:complete", kwargs={"session_id": session.id}))
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# SessionMetaView
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSessionMetaView:
    def test_stores_timezone_offset(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        data = {"session_id": str(session.id), "timezone_offset_minutes": -60}
        response = client.post(
            reverse("tasks:session_meta"),
            data=json.dumps(data),
            content_type="application/json",
        )
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.timezone_offset_minutes == -60

    def test_missing_session_id_returns_422(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(
            reverse("tasks:session_meta"),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# TaskResultSubmitView
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskResultSubmitView:
    def test_login_required(self, client):
        response = client.post(reverse("tasks:submit_result"), data="{}", content_type="application/json")
        assert response.status_code == 302

    def test_422_on_missing_field(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session)
        del payload["task_type"]
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422
        assert "task_type" in response.json()["error"]

    def test_422_on_unknown_task_type(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type="not_a_task")
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_403_on_wrong_user(self, client):
        user1 = _consented_user()
        user2 = _consented_user()
        session = _make_session(user1)
        client.force_login(user2)
        payload = _valid_payload(session)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_409_on_already_complete_session(self, client):
        user = _consented_user()
        session = _make_session(user, status=CognitiveSession.CompletionStatus.COMPLETE)
        client.force_login(user)
        payload = _valid_payload(session)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 409

    def test_201_on_valid_payload(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["ok"] is True
        assert TaskResult.objects.filter(session=session).exists()

    def test_201_returns_next_task(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type=session.task_order[0])
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        body = response.json()
        assert body["next_task"] == session.task_order[1]

    def test_201_next_task_is_null_when_all_done(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        # Submit all tasks except the last
        now_iso = timezone.now().isoformat()
        for task_type in session.task_order[:-1]:
            TaskResult.objects.create(
                session=session,
                task_type=task_type,
                task_version="1.0",
                started_at=timezone.now(),
                completed_at=timezone.now(),
                trial_data=[],
                summary_metrics={},
                session_index_overall=1,
                session_index_per_task=1,
            )
        last_task = session.task_order[-1]
        payload = _valid_payload(session, task_type=last_task)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["next_task"] is None

    def test_session_index_per_task_is_correct(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        task_type = session.task_order[0]
        # First submission
        payload = _valid_payload(session, task_type=task_type)
        client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        result = TaskResult.objects.get(session=session, task_type=task_type)
        assert result.session_index_per_task == 1

    def test_partial_below_threshold_returns_422(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type="pvt", duration_ms=5_000, is_partial=True)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422
        assert TaskResult.objects.filter(session=session).count() == 0

    def test_partial_above_threshold_saves_with_is_partial_true(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type="pvt", duration_ms=35_000, is_partial=True)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        result = TaskResult.objects.get(session=session)
        assert result.is_partial is True

    def test_mood_partial_rejected(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type="mood", duration_ms=0, is_partial=True)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_session_persists_when_partial_below_threshold(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        payload = _valid_payload(session, task_type="pvt", duration_ms=100, is_partial=True)
        response = client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422
        # Session still exists in the DB
        assert CognitiveSession.objects.filter(pk=session.pk).exists()

    def test_interruptions_saved_to_session_on_partial_reject(self, client):
        user = _consented_user()
        session = _make_session(user)
        client.force_login(user)
        interruption = {"type": "visibility_hidden", "at": "2024-01-01T00:00:00Z"}
        payload = _valid_payload(session, task_type="pvt", duration_ms=100, is_partial=True)
        payload["interruptions"] = [interruption]
        client.post(
            reverse("tasks:submit_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        session.refresh_from_db()
        logs = session.device_meta.get("interruption_logs", [])
        assert len(logs) == 1

    def test_invalid_json_returns_422(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(
            reverse("tasks:submit_result"),
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 422

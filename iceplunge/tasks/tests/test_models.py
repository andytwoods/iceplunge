import uuid

import pytest
from django.core.exceptions import ValidationError

from iceplunge.tasks.models import CognitiveSession
from iceplunge.tasks.models import MoodRating
from iceplunge.tasks.models import TaskResult
from iceplunge.users.tests.factories import UserFactory


def _make_session(user):
    return CognitiveSession.objects.create(
        user=user,
        task_order=["pvt", "sart"],
        random_seed="abc123",
    )


def _make_task_result(session, task_type="pvt", index_overall=1, index_per_task=1):
    from django.utils import timezone
    now = timezone.now()
    return TaskResult.objects.create(
        session=session,
        task_type=task_type,
        task_version="1.0",
        started_at=now,
        completed_at=now,
        trial_data=[],
        summary_metrics={},
        session_index_overall=index_overall,
        session_index_per_task=index_per_task,
    )


@pytest.mark.django_db
class TestCognitiveSession:
    def test_uuid_primary_key_persists(self):
        user = UserFactory()
        session = _make_session(user)
        assert session.id is not None
        assert isinstance(session.id, uuid.UUID)
        fetched = CognitiveSession.objects.get(pk=session.id)
        assert fetched.id == session.id

    def test_default_completion_status_is_in_progress(self):
        user = UserFactory()
        session = _make_session(user)
        assert session.completion_status == CognitiveSession.CompletionStatus.IN_PROGRESS


@pytest.mark.django_db
class TestTaskResult:
    def test_invalid_task_type_raises_validation_error(self):
        user = UserFactory()
        session = _make_session(user)
        result = TaskResult(
            session=session,
            task_type="not_a_real_task",
            task_version="1.0",
            started_at=None,
            completed_at=None,
            trial_data=[],
            summary_metrics={},
            session_index_overall=1,
            session_index_per_task=1,
        )
        with pytest.raises(ValidationError):
            result.clean()

    def test_valid_task_type_passes_validation(self):
        user = UserFactory()
        session = _make_session(user)
        result = _make_task_result(session, task_type="pvt")
        result.clean()  # should not raise

    def test_session_index_per_task_stored_correctly(self):
        user = UserFactory()
        session = _make_session(user)
        r1 = _make_task_result(session, task_type="pvt", index_overall=1, index_per_task=1)
        r2 = _make_task_result(session, task_type="pvt", index_overall=2, index_per_task=2)
        assert TaskResult.objects.get(pk=r1.pk).session_index_per_task == 1
        assert TaskResult.objects.get(pk=r2.pk).session_index_per_task == 2


@pytest.mark.django_db
class TestMoodRating:
    def test_mood_rating_str(self):
        user = UserFactory()
        session = _make_session(user)
        mood = MoodRating.objects.create(
            session=session, valence=3, arousal=4, stress=2, sharpness=5
        )
        assert str(mood).startswith("Mood")

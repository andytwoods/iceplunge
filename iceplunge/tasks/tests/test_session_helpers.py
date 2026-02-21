import pytest
from django.utils import timezone

from iceplunge.tasks.helpers.session_helpers import (
    create_session,
    increment_session_indices,
    next_task,
)
from iceplunge.tasks.models import CognitiveSession, TaskResult
from iceplunge.tasks.registry import TASK_REGISTRY
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _make_task_result(session, task_type="pvt"):
    now = timezone.now()
    return TaskResult.objects.create(
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


@pytest.mark.django_db
class TestCreateSession:
    def test_contains_all_registered_task_types(self):
        user = _consented_user()
        session = create_session(user)
        assert set(session.task_order) == set(TASK_REGISTRY.keys())

    def test_task_order_has_no_duplicates(self):
        user = _consented_user()
        session = create_session(user)
        assert len(session.task_order) == len(set(session.task_order))

    def test_same_seed_produces_same_order(self):
        import random

        seed = "test-seed-42"
        task_types = list(TASK_REGISTRY.keys())
        rng1 = random.Random(seed)
        order1 = task_types[:]
        rng1.shuffle(order1)

        rng2 = random.Random(seed)
        order2 = task_types[:]
        rng2.shuffle(order2)

        assert order1 == order2

    def test_session_has_started_at(self):
        user = _consented_user()
        session = create_session(user)
        assert session.started_at is not None

    def test_session_status_is_in_progress(self):
        user = _consented_user()
        session = create_session(user)
        assert session.completion_status == CognitiveSession.CompletionStatus.IN_PROGRESS

    def test_seed_is_stored_on_session(self):
        user = _consented_user()
        session = create_session(user)
        assert len(session.random_seed) > 0

    def test_prompt_event_none_by_default(self):
        user = _consented_user()
        session = create_session(user)
        assert session.prompt_event is None

    def test_is_practice_flag(self):
        user = _consented_user()
        session = create_session(user, is_practice=True)
        assert session.is_practice is True


@pytest.mark.django_db
class TestNextTask:
    def test_returns_first_task_when_none_completed(self):
        user = _consented_user()
        session = create_session(user)
        result = next_task(session)
        assert result == session.task_order[0]

    def test_skips_completed_tasks(self):
        user = _consented_user()
        session = create_session(user)
        first = session.task_order[0]
        _make_task_result(session, task_type=first)
        result = next_task(session)
        assert result == session.task_order[1]

    def test_returns_none_when_all_done(self):
        user = _consented_user()
        session = create_session(user)
        for task_type in session.task_order:
            _make_task_result(session, task_type=task_type)
        assert next_task(session) is None

    def test_order_preserved(self):
        user = _consented_user()
        session = create_session(user)
        results = []
        for _ in session.task_order:
            t = next_task(session)
            results.append(t)
            _make_task_result(session, task_type=t)
        assert results == session.task_order


@pytest.mark.django_db
class TestIncrementSessionIndices:
    def test_overall_index_starts_at_one(self):
        user = _consented_user()
        overall, _ = increment_session_indices(user, "pvt")
        assert overall == 1

    def test_per_task_index_starts_at_one(self):
        user = _consented_user()
        _, per_task = increment_session_indices(user, "pvt")
        assert per_task == 1

    def test_overall_index_increments_across_task_types(self):
        user = _consented_user()
        session = create_session(user)
        now = timezone.now()
        TaskResult.objects.create(
            session=session,
            task_type="pvt",
            task_version="1.0",
            started_at=now,
            completed_at=now,
            trial_data=[],
            summary_metrics={},
            session_index_overall=1,
            session_index_per_task=1,
        )
        overall, _ = increment_session_indices(user, "sart")
        assert overall == 2

    def test_per_task_index_only_counts_same_task(self):
        user = _consented_user()
        session = create_session(user)
        now = timezone.now()
        # Add two pvt results
        for i in range(1, 3):
            TaskResult.objects.create(
                session=session,
                task_type="pvt",
                task_version="1.0",
                started_at=now,
                completed_at=now,
                trial_data=[],
                summary_metrics={},
                session_index_overall=i,
                session_index_per_task=i,
            )
        # sart per-task index should still be 1
        _, per_task = increment_session_indices(user, "sart")
        assert per_task == 1

    def test_different_users_are_independent(self):
        user1 = _consented_user()
        user2 = _consented_user()
        session1 = create_session(user1)
        now = timezone.now()
        TaskResult.objects.create(
            session=session1,
            task_type="pvt",
            task_version="1.0",
            started_at=now,
            completed_at=now,
            trial_data=[],
            summary_metrics={},
            session_index_overall=1,
            session_index_per_task=1,
        )
        overall, per_task = increment_session_indices(user2, "pvt")
        assert overall == 1
        assert per_task == 1

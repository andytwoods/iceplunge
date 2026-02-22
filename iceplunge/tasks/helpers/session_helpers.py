import random
import uuid

from django.utils import timezone

from iceplunge.tasks.registry import TASK_REGISTRY


def create_session(user, prompt_event=None, is_practice=False):
    """
    Create a new CognitiveSession with a deterministic-seeded randomised task order.

    The seed is stored on the session so the order can be reproduced for auditing.
    The signal in tasks/signals.py will compute derived_variables once started_at is set.
    """
    from iceplunge.tasks.models import CognitiveSession  # local import avoids circular

    seed = str(uuid.uuid4())
    rng = random.Random(seed)
    task_types = list(TASK_REGISTRY.keys())
    rng.shuffle(task_types)

    session = CognitiveSession.objects.create(
        user=user,
        prompt_event=prompt_event,
        is_practice=is_practice,
        random_seed=seed,
        task_order=task_types,
        started_at=timezone.now(),
        completion_status=CognitiveSession.CompletionStatus.IN_PROGRESS,
    )
    return session


def create_practice_session(user, task_type):
    """
    Create a single-task practice CognitiveSession (is_practice=True).
    Results are saved but excluded from real analyses.
    """
    from iceplunge.tasks.models import CognitiveSession  # local import avoids circular

    seed = str(uuid.uuid4())
    session = CognitiveSession.objects.create(
        user=user,
        is_practice=True,
        random_seed=seed,
        task_order=[task_type],
        started_at=timezone.now(),
        completion_status=CognitiveSession.CompletionStatus.IN_PROGRESS,
    )
    return session


def next_task(session):
    """
    Return the task_type string of the first uncompleted, non-skipped task in task_order,
    or None if all tasks have a submitted TaskResult or have been skipped.
    """
    completed_types = set(session.task_results.values_list("task_type", flat=True))
    skipped_types = set((session.device_meta or {}).get("skipped_tasks", []))
    done = completed_types | skipped_types
    for task_type in session.task_order:
        if task_type not in done:
            return task_type
    return None


def increment_session_indices(user, task_type):
    """
    Return (overall_index, per_task_index) to be stored on the next TaskResult.

    overall_index  — count of all TaskResults for this user across all sessions + 1.
    per_task_index — count of TaskResults for this user for this task_type + 1.
    """
    from iceplunge.tasks.models import TaskResult  # local import avoids circular

    overall = TaskResult.objects.filter(session__user=user).count() + 1
    per_task = TaskResult.objects.filter(session__user=user, task_type=task_type).count() + 1
    return overall, per_task

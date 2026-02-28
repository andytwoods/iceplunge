import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from iceplunge.tasks.registry import TASK_REGISTRY

# How long an IN_PROGRESS session stays valid before it is auto-abandoned.
# Override via COGNITIVE_SESSION_EXPIRY_HOURS in Django settings.
SESSION_EXPIRY_HOURS: int = getattr(settings, "COGNITIVE_SESSION_EXPIRY_HOURS", 1)


def expire_stale_session(session) -> bool:
    """
    If the session is IN_PROGRESS and older than SESSION_EXPIRY_HOURS, mark it
    ABANDONED and return True.  Returns False if the session is still valid.
    """
    from iceplunge.tasks.models import CognitiveSession  # local import avoids circular

    if session.completion_status != CognitiveSession.CompletionStatus.IN_PROGRESS:
        return False
    cutoff = timezone.now() - timedelta(hours=SESSION_EXPIRY_HOURS)
    if session.started_at and session.started_at < cutoff:
        CognitiveSession.objects.filter(pk=session.pk).update(
            completion_status=CognitiveSession.CompletionStatus.ABANDONED,
        )
        return True
    return False


def create_session(user, prompt_event=None, is_practice=False):
    """
    Create a new CognitiveSession with a deterministic-seeded randomised task order.

    The seed is stored on the session so the order can be reproduced for auditing.
    The signal in tasks/signals.py will compute derived_variables once started_at is set.
    """
    from iceplunge.tasks.models import CognitiveSession  # local import avoids circular

    from iceplunge.tasks.models import TaskConfig, UserTaskPreference  # local import avoids circular

    seed = str(uuid.uuid4())
    rng = random.Random(seed)

    # Global admin-level on/off switches
    globally_enabled = set(
        TaskConfig.objects.filter(is_enabled=True).values_list("task_type", flat=True)
    )

    # Per-user opt-outs
    try:
        pref = UserTaskPreference.objects.get(user=user)
        user_disabled = set(pref.disabled_task_types)
    except UserTaskPreference.DoesNotExist:
        user_disabled = set()

    task_types = [t for t in TASK_REGISTRY if t in globally_enabled and t not in user_disabled]
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

"""
Quality flag computation for CognitiveSession / TaskResult.

All functions are pure (no ORM calls) except flag_rapid_resubmission and
compute_quality_flags which query the DB.

Flag strings follow the naming convention: snake_case identifiers stored in
CognitiveSession.quality_flags (a list of strings).
"""
import datetime

from django.utils import timezone


def flag_anticipation_bursts(trials: list) -> bool:
    """
    Return True if 3 or more anticipation responses occur in a single task.

    Anticipations are identified by is_anticipation=True on the trial dict.
    """
    count = sum(1 for t in trials if t.get("is_anticipation", False))
    return count >= 3


def flag_excessive_misses(trials: list, threshold: float = 0.5) -> bool:
    """
    Return True if more than `threshold` proportion of trials have no response.

    A trial has no response when responded=False (or the key is absent and
    the trial has no rt_ms value).
    """
    if not trials:
        return False
    no_response_count = sum(
        1 for t in trials
        if not t.get("responded", True) or t.get("rt_ms") is None
    )
    return (no_response_count / len(trials)) > threshold


def flag_rapid_resubmission(user, session) -> bool:
    """
    Return True if the user completed another session within the last 10 minutes
    (not counting the given session itself).
    """
    from iceplunge.tasks.models import CognitiveSession

    cutoff = (session.started_at or timezone.now()) - datetime.timedelta(minutes=10)
    return CognitiveSession.objects.filter(
        user=user,
        completion_status=CognitiveSession.CompletionStatus.COMPLETE,
        completed_at__gte=cutoff,
    ).exclude(pk=session.pk).exists()


def flag_visibility_events(session) -> bool:
    """
    Return True if the session's device_meta contains more than 2 interruption log entries
    of type 'visibility_hidden'.
    """
    meta = session.device_meta or {}
    logs = meta.get("interruption_logs", [])
    hidden_count = sum(1 for e in logs if e.get("type") == "visibility_hidden")
    return hidden_count > 2


def compute_quality_flags(user, session, task_result) -> list[str]:
    """
    Compute all quality flags for a TaskResult and return a list of flag strings.

    Flags:
      "anticipation_burst"   — 3+ anticipation responses
      "excessive_misses"     — > 50% of trials have no response
      "rapid_resubmission"   — another completed session within 10 minutes
      "visibility_events"    — > 2 tab-hide interruptions in the session
    """
    trials = task_result.trial_data or []
    flags = []
    if flag_anticipation_bursts(trials):
        flags.append("anticipation_burst")
    if flag_excessive_misses(trials):
        flags.append("excessive_misses")
    if flag_rapid_resubmission(user, session):
        flags.append("rapid_resubmission")
    if flag_visibility_events(session):
        flags.append("visibility_events")
    return flags

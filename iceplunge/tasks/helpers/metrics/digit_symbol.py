"""Server-side summary metric computation for the Digit Symbol Coding task."""


def compute_digit_symbol_summary(trials, duration_ms=None):
    """
    Compute Digit Symbol summary metrics from a list of trial dicts.

    Each trial dict is expected to have:
      correct (bool)        — whether the participant selected the right symbol
      responded (bool)      — whether the participant made a selection (default True)

    Args:
        trials: list of trial dicts
        duration_ms: total task duration in ms; required for correct_per_minute

    Returns dict with:
      correct_per_minute  — total_correct / (duration_ms / 60000), or None if no duration
      total_correct       — count of correct responses
      total_errors        — count of incorrect responses
      error_rate          — total_errors / (total_correct + total_errors), or None if no trials
    """
    total_correct = sum(1 for t in trials if t.get("correct", False))
    total_errors = sum(
        1 for t in trials
        if not t.get("correct", False) and t.get("responded", True)
    )
    total_responses = total_correct + total_errors

    correct_per_minute = None
    if duration_ms is not None and duration_ms > 0:
        correct_per_minute = total_correct / (duration_ms / 60_000)

    error_rate = (total_errors / total_responses) if total_responses > 0 else None

    return {
        "correct_per_minute": correct_per_minute,
        "total_correct": total_correct,
        "total_errors": total_errors,
        "error_rate": error_rate,
    }

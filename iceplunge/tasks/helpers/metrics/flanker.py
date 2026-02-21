"""Server-side summary metric computation for the Eriksen Flanker task."""
import statistics


def compute_flanker_summary(trials):
    """
    Compute Flanker summary metrics from a list of trial dicts.

    Each trial dict is expected to have:
      is_congruent (bool)  — True if all arrows point the same way
      responded (bool)     — whether the participant responded
      correct (bool)       — whether the response was correct
      rt_ms (int | None)   — response time in ms

    Returns dict with:
      congruent_median_rt    — median RT on congruent trials with a response (ms)
      incongruent_median_rt  — median RT on incongruent trials with a response (ms)
      conflict_effect_ms     — incongruent_median_rt - congruent_median_rt
      congruent_accuracy     — proportion correct on congruent trials (float 0–1)
      incongruent_accuracy   — proportion correct on incongruent trials (float 0–1)
    """
    congruent_trials = [t for t in trials if t.get("is_congruent", False)]
    incongruent_trials = [t for t in trials if not t.get("is_congruent", False)]

    congruent_rts = [
        t["rt_ms"] for t in congruent_trials
        if t.get("responded", False) and t.get("rt_ms") is not None
    ]
    incongruent_rts = [
        t["rt_ms"] for t in incongruent_trials
        if t.get("responded", False) and t.get("rt_ms") is not None
    ]

    c_median = statistics.median(congruent_rts) if congruent_rts else None
    i_median = statistics.median(incongruent_rts) if incongruent_rts else None
    conflict_effect_ms = (
        (i_median - c_median) if (i_median is not None and c_median is not None) else None
    )

    congruent_accuracy = (
        sum(1 for t in congruent_trials if t.get("correct", False)) / len(congruent_trials)
        if congruent_trials else None
    )
    incongruent_accuracy = (
        sum(1 for t in incongruent_trials if t.get("correct", False)) / len(incongruent_trials)
        if incongruent_trials else None
    )

    return {
        "congruent_median_rt": c_median,
        "incongruent_median_rt": i_median,
        "conflict_effect_ms": conflict_effect_ms,
        "congruent_accuracy": congruent_accuracy,
        "incongruent_accuracy": incongruent_accuracy,
    }

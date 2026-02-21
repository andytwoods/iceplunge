"""Server-side summary metric computation for the Psychomotor Vigilance Task."""
import statistics


def compute_pvt_summary(trials):
    """
    Compute PVT summary metrics from a list of trial dicts.

    Each trial dict is expected to have:
      rt_ms (int)           — response time in ms (None for non-responses)
      is_anticipation (bool) — RT < 100 ms
      is_lapse (bool)        — RT > 500 ms (or non-response)
      responded (bool)       — whether the participant tapped at all

    Returns dict with:
      median_rt, mean_rt, rt_sd,
      lapse_count (RT > 500 ms),
      anticipation_count (RT < 100 ms),
      valid_trial_count (100 <= RT <= 2000)
    """
    anticipation_count = sum(1 for t in trials if t.get("is_anticipation", False))
    lapse_count = sum(
        1 for t in trials
        if t.get("responded", True) and not t.get("is_anticipation", False) and (t.get("rt_ms") or 0) > 500
    )

    # Valid trials: responses in the 100–2000 ms window
    valid_rts = [
        t["rt_ms"] for t in trials
        if t.get("responded", True)
        and not t.get("is_anticipation", False)
        and t.get("rt_ms") is not None
        and 100 <= t["rt_ms"] <= 2000
    ]

    valid_trial_count = len(valid_rts)

    if not valid_rts:
        return {
            "median_rt": None,
            "mean_rt": None,
            "rt_sd": None,
            "lapse_count": lapse_count,
            "anticipation_count": anticipation_count,
            "valid_trial_count": 0,
        }

    return {
        "median_rt": statistics.median(valid_rts),
        "mean_rt": statistics.mean(valid_rts),
        "rt_sd": statistics.stdev(valid_rts) if len(valid_rts) > 1 else 0.0,
        "lapse_count": lapse_count,
        "anticipation_count": anticipation_count,
        "valid_trial_count": valid_trial_count,
    }

"""Server-side summary metric computation for the SART task."""
import statistics


def compute_sart_summary(trials):
    """
    Compute SART summary metrics from a list of trial dicts.

    Each trial dict is expected to have:
      digit (int)         — 1–9
      is_nogo (bool)      — True if digit == 3 (no-go target)
      responded (bool)    — whether the participant tapped
      rt_ms (int | None)  — response time in ms (None for non-responses)

    Returns dict with:
      commission_errors   — responses on no-go (digit 3) trials
      omission_errors     — non-responses on go trials
      go_median_rt        — median RT across correct go trials (ms)
      go_rt_sd            — SD of go RT (ms)
      post_error_slowing  — mean RT after commission error vs overall go RT (null if < 3 errors)
    """
    go_trials = [t for t in trials if not t.get("is_nogo", False)]
    nogo_trials = [t for t in trials if t.get("is_nogo", False)]

    commission_errors = sum(1 for t in nogo_trials if t.get("responded", False))
    omission_errors = sum(1 for t in go_trials if not t.get("responded", False))

    go_rts = [
        t["rt_ms"] for t in go_trials
        if t.get("responded", False) and t.get("rt_ms") is not None
    ]

    go_median_rt = statistics.median(go_rts) if go_rts else None
    go_rt_sd = statistics.stdev(go_rts) if len(go_rts) > 1 else None

    # Post-error slowing: mean RT on the trial immediately after a commission error
    post_error_slowing = None
    if commission_errors >= 3:
        error_indices = [
            i for i, t in enumerate(trials)
            if t.get("is_nogo", False) and t.get("responded", False)
        ]
        post_error_rts = []
        for idx in error_indices:
            if idx + 1 < len(trials):
                next_t = trials[idx + 1]
                if not next_t.get("is_nogo", False) and next_t.get("responded", False) and next_t.get("rt_ms") is not None:
                    post_error_rts.append(next_t["rt_ms"])
        if post_error_rts and go_median_rt is not None:
            post_error_slowing = statistics.mean(post_error_rts) - go_median_rt

    return {
        "commission_errors": commission_errors,
        "omission_errors": omission_errors,
        "go_median_rt": go_median_rt,
        "go_rt_sd": go_rt_sd,
        "post_error_slowing": post_error_slowing,
    }

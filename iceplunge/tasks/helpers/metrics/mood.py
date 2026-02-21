"""Server-side summary metric computation for the Mood Rating task."""


def compute_mood_summary(trials):
    """
    Extract mood ratings from the trial payload.

    Expects a single trial dict with keys: valence, arousal, stress, sharpness (each 1–5).

    Returns dict with valence, arousal, stress, sharpness (integers 1–5, or None if absent).
    """
    if not trials:
        return {"valence": None, "arousal": None, "stress": None, "sharpness": None}
    trial = trials[0]
    return {
        "valence": trial.get("valence"),
        "arousal": trial.get("arousal"),
        "stress": trial.get("stress"),
        "sharpness": trial.get("sharpness"),
    }

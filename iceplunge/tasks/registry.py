# Registry of all cognitive task types used in the battery.
# Each entry defines metadata used by both the backend and the JS task runner.

TASK_REGISTRY: dict[str, dict] = {
    "pvt": {
        "label": "Psychomotor Vigilance Task",
        "minimum_viable_ms": 30_000,
        "duration_display": "~1 min",
        "duration_ms": 60_000,
        "instructions": (
            "Watch the screen. When a red counter appears, tap it immediately. "
            "The number shows your reaction time in milliseconds — react as fast as you can. "
            "The task runs for about 1 minute."
        ),
    },
    "sart": {
        "label": "Sustained Attention to Response Task",
        "minimum_viable_ms": 30_000,
        "duration_display": "~75 sec",
        "duration_ms": 75_000,
        "instructions": (
            "Digits from 1 to 9 appear one at a time. "
            "Tap the screen for every digit — except 3. "
            "When you see 3, do not tap. "
            "The task runs for about 75 seconds."
        ),
    },
    "flanker": {
        "label": "Eriksen Flanker Task",
        "minimum_viable_ms": 30_000,
        "duration_display": "~75 sec",
        "duration_ms": 75_000,
        "instructions": (
            "A row of arrows will appear. "
            "Tap Left or Right to match the direction of the centre arrow only — "
            "ignore the arrows on either side of it. "
            "The task runs for about 75 seconds."
        ),
    },
    "digit_symbol": {
        "label": "Digit Symbol Coding",
        "minimum_viable_ms": 30_000,
        "duration_display": "~75 sec",
        "duration_ms": 75_000,
        "instructions": (
            "A key at the top shows which symbol matches each digit (0–9). "
            "Each round shows a digit — tap the matching symbol. "
            "Match as many as you can before time runs out (about 75 seconds)."
        ),
    },
    "mood": {
        "label": "Mood Rating",
        "minimum_viable_ms": 0,
        "duration_display": "self-paced",
        "duration_ms": 0,
        "instructions": (
            "Rate how you feel right now on four scales: Mood, Energy, Stress, and Mental Clarity. "
            "Tap a number from 1 (low) to 5 (high) for each scale. "
            "There is no time limit."
        ),
    },
}

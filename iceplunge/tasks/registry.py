# Registry of all cognitive task types used in the battery.
# Each entry defines metadata used by both the backend and the JS task runner.

TASK_REGISTRY: dict[str, dict] = {
    "pvt": {
        "label": "Psychomotor Vigilance Task",
        "minimum_viable_ms": 30_000,
    },
    "sart": {
        "label": "Sustained Attention to Response Task",
        "minimum_viable_ms": 30_000,
    },
    "flanker": {
        "label": "Eriksen Flanker Task",
        "minimum_viable_ms": 30_000,
    },
    "digit_symbol": {
        "label": "Digit Symbol Coding",
        "minimum_viable_ms": 30_000,
    },
    "mood": {
        "label": "Mood Rating",
        "minimum_viable_ms": 0,
    },
}

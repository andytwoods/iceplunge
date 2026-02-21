from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import Model
from django.db.models import PositiveSmallIntegerField
from django.db.models import TextChoices
from django.utils import timezone

User = get_user_model()


class PlungeLog(Model):
    class ImmersionDepth(TextChoices):
        WAIST = "waist", "Waist"
        CHEST = "chest", "Chest"
        NECK = "neck", "Neck"

    class Context(TextChoices):
        PLUNGE_POOL = "plunge_pool", "Plunge pool"
        BATH = "bath", "Bath"
        LAKE = "lake", "Lake"
        SEA = "sea", "Sea"
        CRYOTHERAPY = "cryotherapy", "Cryotherapy"
        OTHER = "other", "Other"

    class PreHotTreatment(TextChoices):
        SAUNA = "sauna", "Sauna"
        STEAM_ROOM = "steam_room", "Steam room"

    class ExerciseTiming(TextChoices):
        BEFORE = "before", "Before"
        AFTER = "after", "After"

    class ExerciseType(TextChoices):
        CARDIO = "cardio", "Cardio"
        WEIGHTS = "weights", "Weights"

    INTENSITY_CHOICES = [
        (1, "No effort"),
        (2, "Mild"),
        (3, "Moderate"),
        (4, "Hard"),
        (5, "Extreme"),
    ]
    INTENSITY_DESCRIPTIONS = [
        "Could have stayed much longer",
        "A little willpower needed",
        "Required real focus",
        "Very tempted to get out",
        "Almost gave up",
    ]

    user = models.ForeignKey(User, on_delete=CASCADE, related_name="plunge_logs")
    timestamp = DateTimeField(default=timezone.now)
    duration_minutes = PositiveSmallIntegerField()
    water_temp_celsius = DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    temp_measured = BooleanField(default=False)
    immersion_depth = CharField(max_length=10, choices=ImmersionDepth.choices)
    context = CharField(max_length=20, choices=Context.choices)
    breathing_technique = CharField(max_length=100, blank=True)
    perceived_intensity = PositiveSmallIntegerField(choices=INTENSITY_CHOICES)
    pre_hot_treatment = CharField(
        max_length=20, choices=PreHotTreatment.choices, null=True, blank=True
    )
    pre_hot_treatment_minutes = PositiveSmallIntegerField(null=True, blank=True)
    exercise_timing = CharField(
        max_length=10, choices=ExerciseTiming.choices, null=True, blank=True
    )
    exercise_type = CharField(
        max_length=10, choices=ExerciseType.choices, null=True, blank=True
    )
    exercise_minutes = PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} \u2013 {self.timestamp:%Y-%m-%d %H:%M}"

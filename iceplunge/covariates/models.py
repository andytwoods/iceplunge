from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import DecimalField
from django.db.models import JSONField
from django.db.models import Model
from django.db.models import OneToOneField
from django.db.models import PositiveSmallIntegerField

User = get_user_model()

SCALE_CHOICES = [(i, str(i)) for i in range(1, 6)]

# ── Schema version constants ───────────────────────────────────────────────────
# Bump the relevant constant whenever a question is added, removed, or its
# scale/wording changes in a way that affects comparability.  All records
# written under the new schema will carry the updated version so that analysis
# pipelines can split or flag data at the version boundary.
#
# DailyCovariate version history:
#   1 – initial: sleep_duration_hours, sleep_quality, alcohol_last_24h, exercise_today
#   2 – added: menstruation_today
DAILY_SCHEMA_VERSION = 2

# WeeklyCovariate version history:
#   1 – initial: gi_severity, gi_symptoms, illness_status
WEEKLY_SCHEMA_VERSION = 1


class DailyCovariate(Model):
    class MenstruationStatus(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        NOT_APPLICABLE = "na", "Not applicable"

    user = models.ForeignKey(User, on_delete=CASCADE, related_name="daily_covariates")
    date = DateField()
    sleep_duration_hours = DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    sleep_quality = PositiveSmallIntegerField(choices=SCALE_CHOICES, null=True, blank=True)
    alcohol_last_24h = BooleanField(null=True, blank=True)
    exercise_today = BooleanField(null=True, blank=True)
    menstruation_today = models.CharField(
        max_length=3,
        choices=MenstruationStatus.choices,
        null=True,
        blank=True,
    )
    schema_version = PositiveSmallIntegerField(default=DAILY_SCHEMA_VERSION, editable=False)

    class Meta:
        unique_together = [("user", "date")]

    def save(self, *args, **kwargs):
        self.schema_version = DAILY_SCHEMA_VERSION
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Daily: {self.user} \u2013 {self.date}"


class WeeklyCovariate(Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="weekly_covariates")
    week_start = DateField()
    gi_severity = PositiveSmallIntegerField(choices=SCALE_CHOICES, null=True, blank=True)
    gi_symptoms = JSONField(default=list, blank=True)
    illness_status = BooleanField(null=True, blank=True)
    schema_version = PositiveSmallIntegerField(default=WEEKLY_SCHEMA_VERSION, editable=False)

    class Meta:
        unique_together = [("user", "week_start")]

    def save(self, *args, **kwargs):
        self.schema_version = WEEKLY_SCHEMA_VERSION
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Weekly: {self.user} \u2013 {self.week_start}"


class SessionCovariate(Model):
    session = OneToOneField(
        "tasks.CognitiveSession",
        on_delete=CASCADE,
        related_name="session_covariate",
    )
    caffeine_since_last_session = BooleanField(null=True, blank=True)
    minutes_since_last_meal = PositiveSmallIntegerField(null=True, blank=True)
    cold_hands = BooleanField(null=True, blank=True)
    wet_hands = BooleanField(null=True, blank=True)

    def __str__(self) -> str:
        return f"SessionCovariate \u2013 {self.session}"

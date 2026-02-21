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


class DailyCovariate(Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="daily_covariates")
    date = DateField()
    sleep_duration_hours = DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    sleep_quality = PositiveSmallIntegerField(choices=SCALE_CHOICES, null=True, blank=True)
    alcohol_last_24h = BooleanField(null=True, blank=True)
    exercise_today = BooleanField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "date")]

    def __str__(self) -> str:
        return f"Daily: {self.user} \u2013 {self.date}"


class WeeklyCovariate(Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="weekly_covariates")
    week_start = DateField()
    gi_severity = PositiveSmallIntegerField(choices=SCALE_CHOICES, null=True, blank=True)
    gi_symptoms = JSONField(default=list, blank=True)
    illness_status = BooleanField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "week_start")]

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

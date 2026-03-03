import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import Model
from django.db.models import SET_NULL
from django.db.models import TextChoices

User = get_user_model()


class PromptEvent(Model):
    class PromptType(TextChoices):
        REACTIVE = "reactive", "Reactive"
        SCHEDULED = "scheduled", "Scheduled"

    user = models.ForeignKey(User, on_delete=CASCADE, related_name="prompt_events")
    scheduled_at = DateTimeField()
    sent_at = DateTimeField(null=True, blank=True)
    opened_at = DateTimeField(null=True, blank=True)
    prompt_type = CharField(max_length=20, choices=PromptType.choices)
    linked_plunge = models.ForeignKey(
        "plunges.PlungeLog",
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="prompt_events",
    )

    def __str__(self) -> str:
        return f"{self.user} \u2013 {self.prompt_type} \u2013 {self.scheduled_at:%Y-%m-%d %H:%M}"


class NotificationProfile(Model):
    """Per-user push notification settings and OneSignal player ID."""

    user = models.OneToOneField(User, on_delete=CASCADE, related_name="notification_profile")
    onesignal_player_id = CharField(max_length=255, blank=True)
    push_enabled = models.BooleanField(default=True)
    notifications_per_day = models.PositiveSmallIntegerField(
        default=2,
        choices=[(i, str(i)) for i in range(0, 7)],
    )
    window_start = models.TimeField(default=datetime.time(8, 0))
    window_end = models.TimeField(default=datetime.time(22, 0))

    def __str__(self) -> str:
        return f"NotificationProfile \u2013 {self.user}"

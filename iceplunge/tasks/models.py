from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import JSONField
from django.db.models import Model
from django.db.models import OneToOneField
from django.db.models import PositiveIntegerField
from django.db.models import PositiveSmallIntegerField
from django.db.models import SET_NULL
from django.db.models import SmallIntegerField
from django.db.models import TextChoices
from django.db.models import UUIDField

from iceplunge.tasks.registry import TASK_REGISTRY

User = get_user_model()


class CognitiveSession(Model):
    class CompletionStatus(TextChoices):
        COMPLETE = "complete", "Complete"
        ABANDONED = "abandoned", "Abandoned"
        IN_PROGRESS = "in_progress", "In Progress"

    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="cognitive_sessions")
    prompt_event = models.ForeignKey(
        "notifications.PromptEvent",
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="cognitive_sessions",
    )
    started_at = DateTimeField(null=True, blank=True)
    completed_at = DateTimeField(null=True, blank=True)
    task_order = JSONField()
    random_seed = CharField(max_length=64)
    device_meta = JSONField(default=dict)
    timezone_offset_minutes = SmallIntegerField(null=True, blank=True)
    completion_status = CharField(
        max_length=20,
        choices=CompletionStatus.choices,
        default=CompletionStatus.IN_PROGRESS,
    )
    quality_flags = JSONField(default=list)
    is_practice = BooleanField(default=False)
    derived_variables = JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["user", "completion_status"]),
        ]

    def __str__(self) -> str:
        return f"Session {self.id} \u2013 {self.user}"


class TaskResult(Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    session = models.ForeignKey(CognitiveSession, on_delete=CASCADE, related_name="task_results")
    task_type = CharField(max_length=50)
    task_version = CharField(max_length=20)
    started_at = DateTimeField()
    completed_at = DateTimeField()
    trial_data = JSONField()
    summary_metrics = JSONField()
    session_index_overall = PositiveIntegerField()
    session_index_per_task = PositiveIntegerField()
    is_acclimatisation = BooleanField(default=False)
    is_partial = BooleanField(default=False)

    def clean(self):
        if self.task_type not in TASK_REGISTRY:
            raise ValidationError(
                {"task_type": f"'{self.task_type}' is not a registered task type."}
            )

    def __str__(self) -> str:
        return f"{self.task_type} v{self.task_version} \u2013 {self.session}"


class MoodRating(Model):
    SCALE_CHOICES = [(i, str(i)) for i in range(1, 6)]

    session = OneToOneField(CognitiveSession, on_delete=CASCADE, related_name="mood_rating")
    valence = PositiveSmallIntegerField(choices=SCALE_CHOICES)
    arousal = PositiveSmallIntegerField(choices=SCALE_CHOICES)
    stress = PositiveSmallIntegerField(choices=SCALE_CHOICES)
    sharpness = PositiveSmallIntegerField(choices=SCALE_CHOICES)

    def __str__(self) -> str:
        return f"Mood \u2013 {self.session}"

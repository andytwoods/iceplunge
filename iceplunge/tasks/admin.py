from django.contrib import admin

from .models import CognitiveSession
from .models import MoodRating
from .models import TaskConfig
from .models import TaskResult


@admin.register(CognitiveSession)
class CognitiveSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "started_at", "completion_status", "is_practice"]
    list_filter = ["completion_status", "is_practice"]
    search_fields = ["user__email"]
    ordering = ["-started_at"]


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "task_type", "task_version", "is_partial"]
    list_filter = ["task_type", "is_partial", "is_acclimatisation"]
    search_fields = ["session__user__email"]


@admin.register(TaskConfig)
class TaskConfigAdmin(admin.ModelAdmin):
    list_display = ["task_label", "task_type", "is_enabled"]
    list_editable = ["is_enabled"]
    ordering = ["task_type"]

    @admin.display(description="Task")
    def task_label(self, obj):
        from iceplunge.tasks.registry import TASK_REGISTRY
        return TASK_REGISTRY.get(obj.task_type, {}).get("label", obj.task_type)


@admin.register(MoodRating)
class MoodRatingAdmin(admin.ModelAdmin):
    list_display = ["session", "valence", "arousal", "stress", "sharpness"]

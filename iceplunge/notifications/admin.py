from django.contrib import admin

from .models import NotificationProfile
from .models import PromptEvent


@admin.register(PromptEvent)
class PromptEventAdmin(admin.ModelAdmin):
    list_display = ["user", "prompt_type", "scheduled_at", "sent_at", "opened_at"]
    list_filter = ["prompt_type"]
    search_fields = ["user__email"]
    ordering = ["-scheduled_at"]


@admin.register(NotificationProfile)
class NotificationProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "push_enabled", "morning_window_start", "evening_window_start"]
    list_filter = ["push_enabled"]
    search_fields = ["user__email"]

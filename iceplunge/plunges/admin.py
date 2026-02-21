from django.contrib import admin

from .models import PlungeLog


@admin.register(PlungeLog)
class PlungeLogAdmin(admin.ModelAdmin):
    list_display = ["user", "timestamp", "context", "duration_minutes", "perceived_intensity"]
    list_filter = ["context", "immersion_depth"]
    search_fields = ["user__email"]
    ordering = ["-timestamp"]

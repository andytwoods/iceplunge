from django.contrib import admin

from .models import DailyCovariate
from .models import SessionCovariate
from .models import WeeklyCovariate


@admin.register(DailyCovariate)
class DailyCovariateAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "sleep_duration_hours", "sleep_quality"]
    search_fields = ["user__email"]
    ordering = ["-date"]


@admin.register(WeeklyCovariate)
class WeeklyCovariateAdmin(admin.ModelAdmin):
    list_display = ["user", "week_start", "gi_severity", "illness_status"]
    search_fields = ["user__email"]
    ordering = ["-week_start"]


@admin.register(SessionCovariate)
class SessionCovariateAdmin(admin.ModelAdmin):
    list_display = ["session", "caffeine_since_last_session", "minutes_since_last_meal", "cold_hands", "wet_hands"]
    search_fields = ["session__user__email"]

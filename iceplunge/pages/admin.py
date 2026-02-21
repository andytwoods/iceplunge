from django.contrib import admin

from .models import Sponsor


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ("name", "tier", "is_active", "order")
    list_filter = ("tier", "is_active")
    list_editable = ("is_active", "order")
    ordering = ("order", "name")

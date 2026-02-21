"""Management command to manually trigger the daily prompt dispatch."""
import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from iceplunge.notifications.helpers.scheduling import schedule_daily_prompts_for_user
from iceplunge.notifications.models import NotificationProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dispatch morning and evening push-notification prompts for all opted-in users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=lambda s: datetime.date.fromisoformat(s),
            default=None,
            help="Date to schedule prompts for (YYYY-MM-DD). Defaults to today.",
        )

    def handle(self, *args, **options):
        target_date = options["date"] or timezone.now().date()
        self.stdout.write(f"Dispatching prompts for {target_date}…")
        profiles = NotificationProfile.objects.filter(push_enabled=True).select_related("user")
        count = 0
        for profile in profiles:
            created = schedule_daily_prompts_for_user(profile.user, target_date)
            count += len(created)
        self.stdout.write(self.style.SUCCESS(f"Done — {count} PromptEvent(s) created."))

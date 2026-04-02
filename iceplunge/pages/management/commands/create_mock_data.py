"""
Management command to populate mock dashboard data for local development.

Usage:
    python manage.py create_mock_data
    python manage.py create_mock_data --email user@example.com
    python manage.py create_mock_data --days 60
    python manage.py create_mock_data --clear
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from iceplunge.plunges.models import PlungeLog
from iceplunge.tasks.models import CognitiveSession, MoodRating, TaskResult

User = get_user_model()


class Command(BaseCommand):
    help = "Generate mock dashboard data for a user"

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, default="andytwoods@gmail.com")
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing mock sessions before creating new ones",
        )

    def handle(self, *args, **options):
        email = options["email"]
        days = options["days"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(f"No user found with email: {email}")
            return

        if options["clear"]:
            deleted, _ = CognitiveSession.objects.filter(user=user).delete()
            PlungeLog.objects.filter(user=user).delete()
            self.stdout.write(f"Cleared {deleted} existing sessions.")

        now = timezone.now()
        # Simulate gradual improvement: RT starts ~380ms, trends down to ~280ms
        # Lapses start ~4, trend down to ~1
        # Mood starts lower, trends up slightly

        # Create plunges roughly every 2-3 days
        plunges_created = 0
        for i in range(days):
            if i % random.randint(2, 3) == 0:
                plunge_time = now - timedelta(days=(days - i), hours=random.randint(7, 19))
                PlungeLog.objects.create(
                    user=user,
                    timestamp=plunge_time,
                    duration_minutes=random.randint(2, 8),
                    water_temp_celsius=round(random.uniform(8, 15), 1),
                    immersion_depth=random.choice(["WAIST", "CHEST", "NECK"]),
                    context=random.choice(["PLUNGE_POOL", "LAKE", "SEA", "BATH"]),
                    perceived_intensity=random.randint(2, 5),
                )
                plunges_created += 1

        sessions_created = 0
        for i in range(days):
            # ~70% chance of a session on any given day
            if random.random() > 0.70:
                continue

            day_offset = days - i  # oldest first
            session_time = now - timedelta(days=day_offset, hours=random.randint(6, 20))
            progress = i / max(days - 1, 1)  # 0.0 → 1.0

            session = CognitiveSession.objects.create(
                user=user,
                started_at=session_time,
                completed_at=session_time + timedelta(minutes=random.randint(8, 15)),
                completion_status=CognitiveSession.CompletionStatus.COMPLETE,
                task_order=["pvt", "mood"],
                random_seed="mock",
            )

            # PVT: reaction time improves with practice, add some noise
            base_rt = 380 - (progress * 100)
            median_rt = int(base_rt + random.gauss(0, 25))
            median_rt = max(200, min(600, median_rt))

            base_lapses = 4 - (progress * 3)
            lapse_count = max(0, int(base_lapses + random.gauss(0, 1)))

            TaskResult.objects.create(
                session=session,
                task_type="pvt",
                task_version="1.0",
                started_at=session_time,
                completed_at=session_time + timedelta(minutes=5),
                trial_data=[],
                summary_metrics={"median_rt": median_rt, "lapse_count": lapse_count},
                session_index_overall=0,
                session_index_per_task=0,
                is_partial=False,
            )

            # Mood: slight upward trend with noise
            def mood_val(base, trend=0.5):
                raw = base + (progress * trend) + random.gauss(0, 0.6)
                return max(1, min(5, round(raw)))

            MoodRating.objects.create(
                session=session,
                valence=mood_val(2.8, trend=1.0),
                arousal=mood_val(3.0, trend=0.5),
                stress=mood_val(3.2, trend=-0.8),   # stress decreases
                sharpness=mood_val(2.5, trend=1.2),
            )

            sessions_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {sessions_created} mock sessions and {plunges_created} plunges for {email} over {days} days."
            )
        )

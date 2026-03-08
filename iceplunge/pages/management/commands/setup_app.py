from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from allauth.account.models import EmailAddress

User = get_user_model()


class Command(BaseCommand):
    help = "One-shot setup: create superuser, seed challenges and survey questions."

    def handle(self, *args, **kwargs):
        self._create_superuser()
        self._setup_strava_socialapp()

    def _create_superuser(self):
        email = "andytwoods@gmail.com"
        new_password = get_random_string(10)
        try:
            if not User.objects.filter(is_superuser=True).exists():
                self.stdout.write("No superusers found, creating one")
                User.objects.create_superuser(email=email, password=new_password)
                self.stdout.write("=======================")
                self.stdout.write("A superuser has been created")
                self.stdout.write(f"Email: {email}")
                self.stdout.write(f"Password: {new_password}")
                self.stdout.write("=======================")
            else:
                self.stdout.write("A superuser exists in the database. Skipping.")
        except Exception as e:
            self.stderr.write(f"There was an error creating superuser: {e}")

    def _setup_strava_socialapp(self):
        """Create the allauth SocialApp for Strava if it doesn't already exist."""
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site

        client_id = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get(
            "strava", {}
        ).get("APP", {}).get("client_id", "")
        secret = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get(
            "strava", {}
        ).get("APP", {}).get("secret", "")

        if not client_id or not secret:
            self.stdout.write(
                "STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET not set — skipping Strava SocialApp setup."
            )
            return

        if SocialApp.objects.filter(provider="strava").exists():
            self.stdout.write("Strava SocialApp already exists. Skipping.")
            return

        app = SocialApp.objects.create(
            provider="strava",
            name="Strava",
            client_id=client_id,
            secret=secret,
        )
        app.sites.set(Site.objects.all())
        self.stdout.write("Strava SocialApp created successfully.")

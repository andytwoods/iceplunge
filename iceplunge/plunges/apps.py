from django.apps import AppConfig


class PlungesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iceplunge.plunges"

    def ready(self):
        import iceplunge.plunges.signals  # noqa: F401

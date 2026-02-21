from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iceplunge.tasks"

    def ready(self):
        import iceplunge.tasks.signals  # noqa: F401

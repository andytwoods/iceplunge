"""Seed TaskConfig with one enabled row for every registered task type."""

from django.db import migrations


def seed_task_configs(apps, schema_editor):
    from iceplunge.tasks.registry import TASK_REGISTRY

    TaskConfig = apps.get_model("tasks", "TaskConfig")
    for task_type in TASK_REGISTRY:
        TaskConfig.objects.get_or_create(task_type=task_type, defaults={"is_enabled": True})


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_taskconfig"),
    ]

    operations = [
        migrations.RunPython(seed_task_configs, migrations.RunPython.noop),
    ]

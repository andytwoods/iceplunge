import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_fix_timefield_defaults"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notificationprofile",
            name="morning_window_start",
        ),
        migrations.RemoveField(
            model_name="notificationprofile",
            name="evening_window_start",
        ),
        migrations.AddField(
            model_name="notificationprofile",
            name="notifications_per_day",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"), (6, "6")],
                default=2,
            ),
        ),
        migrations.AddField(
            model_name="notificationprofile",
            name="window_start",
            field=models.TimeField(default=datetime.time(8, 0)),
        ),
        migrations.AddField(
            model_name="notificationprofile",
            name="window_end",
            field=models.TimeField(default=datetime.time(22, 0)),
        ),
    ]

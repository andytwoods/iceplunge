import datetime

import pytest
from django.db import IntegrityError

from iceplunge.covariates.models import DailyCovariate
from iceplunge.covariates.models import WeeklyCovariate
from iceplunge.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDailyCovariate:
    def test_unique_together_user_date(self):
        user = UserFactory()
        date = datetime.date(2024, 1, 15)
        DailyCovariate.objects.create(user=user, date=date)
        with pytest.raises(IntegrityError):
            DailyCovariate.objects.create(user=user, date=date)

    def test_different_dates_allowed(self):
        user = UserFactory()
        DailyCovariate.objects.create(user=user, date=datetime.date(2024, 1, 15))
        DailyCovariate.objects.create(user=user, date=datetime.date(2024, 1, 16))
        assert DailyCovariate.objects.filter(user=user).count() == 2

    def test_str(self):
        user = UserFactory()
        date = datetime.date(2024, 1, 15)
        cov = DailyCovariate.objects.create(user=user, date=date)
        assert str(cov) == f"Daily: {user} \u2013 {date}"


@pytest.mark.django_db
class TestWeeklyCovariate:
    def test_unique_together_user_week_start(self):
        user = UserFactory()
        week_start = datetime.date(2024, 1, 15)
        WeeklyCovariate.objects.create(user=user, week_start=week_start)
        with pytest.raises(IntegrityError):
            WeeklyCovariate.objects.create(user=user, week_start=week_start)

    def test_str(self):
        user = UserFactory()
        week_start = datetime.date(2024, 1, 15)
        cov = WeeklyCovariate.objects.create(user=user, week_start=week_start)
        assert str(cov) == f"Weekly: {user} \u2013 {week_start}"

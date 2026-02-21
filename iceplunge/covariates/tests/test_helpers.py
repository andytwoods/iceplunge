import datetime

import pytest

from iceplunge.covariates.helpers import needs_daily_covariate
from iceplunge.covariates.helpers import needs_weekly_covariate
from iceplunge.covariates.models import DailyCovariate
from iceplunge.covariates.models import WeeklyCovariate
from iceplunge.users.tests.factories import UserFactory

TODAY = datetime.date(2024, 6, 17)          # a Monday
WEEK_START = datetime.date(2024, 6, 17)     # same Monday


@pytest.mark.django_db
class TestNeedsDailyCovariate:
    def test_no_record_returns_true(self):
        user = UserFactory()
        assert needs_daily_covariate(user, today=TODAY) is True

    def test_record_exists_returns_false(self):
        user = UserFactory()
        DailyCovariate.objects.create(user=user, date=TODAY)
        assert needs_daily_covariate(user, today=TODAY) is False

    def test_record_for_different_day_still_returns_true(self):
        user = UserFactory()
        yesterday = TODAY - datetime.timedelta(days=1)
        DailyCovariate.objects.create(user=user, date=yesterday)
        assert needs_daily_covariate(user, today=TODAY) is True

    def test_different_user_not_counted(self):
        user1 = UserFactory()
        user2 = UserFactory()
        DailyCovariate.objects.create(user=user1, date=TODAY)
        assert needs_daily_covariate(user2, today=TODAY) is True


@pytest.mark.django_db
class TestNeedsWeeklyCovariate:
    def test_no_record_returns_true(self):
        user = UserFactory()
        assert needs_weekly_covariate(user, today=TODAY) is True

    def test_record_exists_returns_false(self):
        user = UserFactory()
        WeeklyCovariate.objects.create(user=user, week_start=WEEK_START)
        assert needs_weekly_covariate(user, today=TODAY) is False

    def test_record_from_previous_week_returns_true(self):
        user = UserFactory()
        last_week_start = WEEK_START - datetime.timedelta(weeks=1)
        WeeklyCovariate.objects.create(user=user, week_start=last_week_start)
        assert needs_weekly_covariate(user, today=TODAY) is True

    def test_mid_week_resolves_to_correct_monday(self):
        """Wednesday 2024-06-19 should resolve to Monday 2024-06-17."""
        user = UserFactory()
        wednesday = datetime.date(2024, 6, 19)
        WeeklyCovariate.objects.create(user=user, week_start=WEEK_START)
        assert needs_weekly_covariate(user, today=wednesday) is False

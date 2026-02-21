import datetime
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.covariates.models import DailyCovariate
from iceplunge.covariates.models import WeeklyCovariate
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory

TODAY = datetime.date(2024, 6, 17)
WEEK_START = datetime.date(2024, 6, 17)  # Monday


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _patch_today(view_module_path, today):
    """Context manager that freezes datetime.date.today() in the given module."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch(f"{view_module_path}.datetime") as mock_dt:
            mock_dt.date.today.return_value = today
            mock_dt.timedelta = datetime.timedelta
            yield mock_dt

    return _ctx()


@pytest.mark.django_db
class TestDailyCovariateView:
    VIEW_MODULE = "iceplunge.covariates.views"

    def test_login_required(self, client):
        response = client.post(reverse("covariates:daily"), data={})
        assert response.status_code == 302

    def test_post_creates_record(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {
            "sleep_duration_hours": "7.5",
            "sleep_quality": "4",
            "alcohol_last_24h": False,
            "exercise_today": True,
        }
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(reverse("covariates:daily"), data=data)
        assert DailyCovariate.objects.filter(user=user, date=TODAY).exists()
        assert response.status_code == 302

    def test_post_twice_updates_not_duplicates(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {"sleep_duration_hours": "7.0", "sleep_quality": "3",
                "alcohol_last_24h": False, "exercise_today": False}
        with _patch_today(self.VIEW_MODULE, TODAY):
            client.post(reverse("covariates:daily"), data=data)
            data["sleep_duration_hours"] = "8.0"
            client.post(reverse("covariates:daily"), data=data)
        records = DailyCovariate.objects.filter(user=user, date=TODAY)
        assert records.count() == 1
        assert records.first().sleep_duration_hours == pytest.approx(8.0, abs=0.01)

    def test_htmx_post_returns_success_partial(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {"sleep_duration_hours": "6.0", "sleep_quality": "2",
                "alcohol_last_24h": False, "exercise_today": False}
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(
                reverse("covariates:daily"), data=data, HTTP_HX_REQUEST="true"
            )
        assert response.status_code == 200
        assert b"saved" in response.content.lower() or b"thank" in response.content.lower()


@pytest.mark.django_db
class TestWeeklyCovariateView:
    VIEW_MODULE = "iceplunge.covariates.views"

    def test_post_creates_record(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {"gi_severity": "2", "illness_status": False}
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(reverse("covariates:weekly"), data=data)
        assert WeeklyCovariate.objects.filter(user=user, week_start=WEEK_START).exists()
        assert response.status_code == 302

    def test_post_twice_updates_not_duplicates(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {"gi_severity": "1", "illness_status": False}
        with _patch_today(self.VIEW_MODULE, TODAY):
            client.post(reverse("covariates:weekly"), data=data)
            data["gi_severity"] = "3"
            client.post(reverse("covariates:weekly"), data=data)
        records = WeeklyCovariate.objects.filter(user=user, week_start=WEEK_START)
        assert records.count() == 1
        assert records.first().gi_severity == 3

    def test_htmx_post_returns_success_partial(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {"gi_severity": "2", "gi_symptoms": [], "illness_status": False}
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(
                reverse("covariates:weekly"), data=data, HTTP_HX_REQUEST="true"
            )
        assert response.status_code == 200
        assert b"saved" in response.content.lower() or b"thank" in response.content.lower()


@pytest.mark.django_db
class TestMoreInfoView:
    VIEW_MODULE = "iceplunge.covariates.views"

    def test_login_required(self, client):
        response = client.get(reverse("covariates:more_info"))
        assert response.status_code == 302

    def test_htmx_get_returns_form(self, client):
        user = _consented_user()
        client.force_login(user)
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.get(
                reverse("covariates:more_info"), HTTP_HX_REQUEST="true"
            )
        assert response.status_code == 200
        assert b"sleep" in response.content.lower()

    def test_post_creates_both_records(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {
            "sleep_duration_hours": "7.5",
            "sleep_quality": "4",
            "alcohol_last_24h": "False",
            "exercise_today": "True",
            "gi_severity": "2",
            "illness_status": "False",
        }
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(reverse("covariates:more_info"), data=data)
        assert DailyCovariate.objects.filter(user=user, date=TODAY).exists()
        assert WeeklyCovariate.objects.filter(user=user, week_start=WEEK_START).exists()
        assert response.status_code == 302

    def test_post_twice_updates_not_duplicates(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {
            "sleep_duration_hours": "7.0",
            "sleep_quality": "3",
            "alcohol_last_24h": "False",
            "exercise_today": "False",
            "gi_severity": "1",
            "illness_status": "False",
        }
        with _patch_today(self.VIEW_MODULE, TODAY):
            client.post(reverse("covariates:more_info"), data=data)
            data["sleep_duration_hours"] = "8.0"
            data["gi_severity"] = "3"
            client.post(reverse("covariates:more_info"), data=data)
        assert DailyCovariate.objects.filter(user=user, date=TODAY).count() == 1
        assert WeeklyCovariate.objects.filter(user=user, week_start=WEEK_START).count() == 1
        daily = DailyCovariate.objects.get(user=user, date=TODAY)
        assert daily.sleep_duration_hours == pytest.approx(8.0, abs=0.01)
        weekly = WeeklyCovariate.objects.get(user=user, week_start=WEEK_START)
        assert weekly.gi_severity == 3

    def test_htmx_post_returns_success_partial(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {
            "sleep_duration_hours": "8.0",
            "sleep_quality": "5",
            "alcohol_last_24h": "False",
            "exercise_today": "False",
            "gi_severity": "1",
            "illness_status": "False",
        }
        with _patch_today(self.VIEW_MODULE, TODAY):
            response = client.post(
                reverse("covariates:more_info"), data=data, HTTP_HX_REQUEST="true"
            )
        assert response.status_code == 200
        assert b"wellbeing" in response.content.lower() or b"saved" in response.content.lower()

    def test_post_with_gi_symptoms(self, client):
        user = _consented_user()
        client.force_login(user)
        data = {
            "sleep_duration_hours": "6.5",
            "sleep_quality": "3",
            "alcohol_last_24h": "False",
            "exercise_today": "True",
            "gi_severity": "3",
            "gi_symptoms": ["bloating", "nausea"],
            "illness_status": "False",
        }
        with _patch_today(self.VIEW_MODULE, TODAY):
            client.post(reverse("covariates:more_info"), data=data)
        weekly = WeeklyCovariate.objects.get(user=user, week_start=WEEK_START)
        assert "bloating" in weekly.gi_symptoms
        assert "nausea" in weekly.gi_symptoms

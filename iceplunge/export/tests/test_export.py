"""Tests for research data export views."""
import csv
import io
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.tasks.helpers.session_helpers import create_session
from iceplunge.tasks.models import CognitiveSession, TaskResult
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory



def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _superuser():
    user = UserFactory()
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _complete_session(user):
    session = create_session(user)
    CognitiveSession.objects.filter(pk=session.pk).update(
        completion_status=CognitiveSession.CompletionStatus.COMPLETE,
        completed_at=timezone.now(),
    )
    session.refresh_from_db()
    return session


def _pvt_result(session):
    now = timezone.now()
    return TaskResult.objects.create(
        session=session,
        task_type="pvt",
        task_version="1.0",
        started_at=now,
        completed_at=now,
        trial_data=[
            {"trial_index": 0, "stimulus_at_ms": 1000, "response_at_ms": 1320, "rt_ms": 320, "correct": True},
        ],
        summary_metrics={"median_rt": 320, "lapse_count": 0},
        session_index_overall=1,
        session_index_per_task=1,
        is_partial=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Access control (common to all export views)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestExportAccessControl:
    @pytest.mark.parametrize("view_name", ["export:session_csv", "export:trial_csv", "export:full_json"])
    def test_anonymous_redirected(self, client, view_name):
        response = client.get(reverse(view_name))
        assert response.status_code == 302

    @pytest.mark.parametrize("view_name", ["export:session_csv", "export:trial_csv", "export:full_json"])
    def test_regular_user_forbidden(self, client, view_name):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse(view_name))
        assert response.status_code in (302, 403)

    @pytest.mark.parametrize("view_name", ["export:session_csv", "export:trial_csv", "export:full_json"])
    def test_superuser_allowed(self, client, view_name):
        user = _superuser()
        client.force_login(user)
        response = client.get(reverse(view_name))
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Session CSV export
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionCsvExport:
    def _get(self, client, **params):
        url = reverse("export:session_csv")
        admin = _superuser()
        client.force_login(admin)
        return client.get(url, params)

    def test_returns_csv_content_type(self, client):
        response = self._get(client)
        assert "text/csv" in response["Content-Type"]

    def test_has_content_disposition(self, client):
        response = self._get(client)
        assert "attachment" in response["Content-Disposition"]
        assert ".csv" in response["Content-Disposition"]

    def test_empty_export_has_only_header(self, client):
        response = self._get(client)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 1  # header only

    def test_complete_session_appears_in_export(self, client):
        user = _consented_user()
        _complete_session(user)
        response = self._get(client)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 2  # header + 1 data row

    def test_incomplete_session_excluded(self, client):
        user = _consented_user()
        create_session(user)  # IN_PROGRESS, not complete
        response = self._get(client)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 1  # header only

    def test_pseudonymised_id_not_email(self, client):
        user = _consented_user()
        _complete_session(user)
        response = self._get(client)
        content = response.content.decode()
        assert user.email not in content
        assert str(user.id) in content

    def test_date_filter_from_date(self, client):
        user = _consented_user()
        _complete_session(user)
        response = self._get(client, from_date="2099-01-01")
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 1  # no sessions that far in the future


# ─────────────────────────────────────────────────────────────────────────────
# Trial CSV export
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTrialCsvExport:
    def _get(self, client, **params):
        url = reverse("export:trial_csv")
        admin = _superuser()
        client.force_login(admin)
        return client.get(url, params)

    def test_returns_csv_content_type(self, client):
        response = self._get(client)
        assert "text/csv" in response["Content-Type"]

    def test_trial_rows_appear(self, client):
        user = _consented_user()
        session = _complete_session(user)
        _pvt_result(session)
        response = self._get(client)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        # header + 1 trial row
        assert len(rows) == 2

    def test_partial_results_excluded(self, client):
        user = _consented_user()
        session = _complete_session(user)
        now = timezone.now()
        TaskResult.objects.create(
            session=session,
            task_type="pvt",
            task_version="1.0",
            started_at=now,
            completed_at=now,
            trial_data=[{"trial_index": 0}],
            summary_metrics={},
            session_index_overall=1,
            session_index_per_task=1,
            is_partial=True,
        )
        response = self._get(client)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 1  # header only


# ─────────────────────────────────────────────────────────────────────────────
# Full JSON export
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFullJsonExport:
    def _get(self, client, **params):
        url = reverse("export:full_json")
        admin = _superuser()
        client.force_login(admin)
        return client.get(url, params)

    def test_returns_json_content_type(self, client):
        response = self._get(client)
        assert "application/json" in response["Content-Type"]

    def test_empty_export_returns_empty_list(self, client):
        response = self._get(client)
        data = json.loads(response.content)
        assert data == []

    def test_session_and_task_results_nested(self, client):
        user = _consented_user()
        session = _complete_session(user)
        _pvt_result(session)
        response = self._get(client)
        data = json.loads(response.content)
        assert len(data) == 1
        entry = data[0]
        assert entry["participant_id"] == str(user.id)
        assert "session_id" in entry
        assert len(entry["task_results"]) == 1
        assert entry["task_results"][0]["task_type"] == "pvt"

    def test_no_pii_in_export(self, client):
        user = _consented_user()
        _complete_session(user)
        response = self._get(client)
        content = response.content.decode()
        assert user.email not in content
        if hasattr(user, "name") and user.name:
            assert user.name not in content

    def test_date_filter_to_date(self, client):
        user = _consented_user()
        _complete_session(user)
        response = self._get(client, to_date="2000-01-01")
        data = json.loads(response.content)
        assert data == []

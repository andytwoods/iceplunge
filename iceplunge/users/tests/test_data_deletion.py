"""Tests for the self-service data deletion flow (T10.1)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from iceplunge.plunges.models import PlungeLog
from iceplunge.tasks.helpers.session_helpers import create_session
from iceplunge.tasks.models import CognitiveSession, TaskResult
from iceplunge.users.models import BaselineProfile, ConsentProfile
from iceplunge.users.tests.factories import UserFactory

User = get_user_model()


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


# ─────────────────────────────────────────────────────────────────────────────
# DataDeletionView — GET
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDataDeletionViewGet:
    def _url(self):
        return reverse("users:delete_data")

    def test_requires_login(self, client):
        response = client.get(self._url())
        assert response.status_code == 302
        assert "/accounts/" in response["Location"] or "login" in response["Location"]

    def test_renders_200_for_authenticated_user(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        assert response.status_code == 200

    def test_page_mentions_permanent_deletion(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(self._url())
        content = response.content.decode().lower()
        assert "permanent" in content or "cannot be undone" in content or "delete" in content


# ─────────────────────────────────────────────────────────────────────────────
# DataDeletionView — POST
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDataDeletionViewPost:
    def _url(self):
        return reverse("users:delete_data")

    def test_post_without_confirm_stays_on_page(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(self._url(), {})
        assert response.status_code == 200
        assert User.objects.filter(pk=user.pk).exists()

    def test_post_with_confirm_deletes_user(self, client):
        user = _consented_user()
        user_pk = user.pk
        client.force_login(user)
        response = client.post(self._url(), {"confirm": "yes"})
        assert not User.objects.filter(pk=user_pk).exists()

    def test_post_with_confirm_redirects_to_complete(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(self._url(), {"confirm": "yes"})
        assert response.status_code == 302
        assert response["Location"] == reverse("users:deletion_complete")

    def test_post_cascades_to_plunge_logs(self, client):
        user = _consented_user()
        PlungeLog.objects.create(
            user=user,
            timestamp=timezone.now(),
            duration_minutes=5,
            water_temp_celsius=10.0,
            immersion_depth="chest",
            context="bath",
            perceived_intensity=3,
        )
        user_pk = user.pk
        client.force_login(user)
        client.post(self._url(), {"confirm": "yes"})
        assert not PlungeLog.objects.filter(user_id=user_pk).exists()

    def test_post_cascades_to_cognitive_sessions(self, client):
        user = _consented_user()
        create_session(user)
        user_pk = user.pk
        client.force_login(user)
        client.post(self._url(), {"confirm": "yes"})
        assert not CognitiveSession.objects.filter(user_id=user_pk).exists()

    def test_post_logs_out_user(self, client):
        user = _consented_user()
        client.force_login(user)
        client.post(self._url(), {"confirm": "yes"})
        # Subsequent authenticated request should redirect to login
        response = client.get(reverse("users:delete_data"))
        assert response.status_code == 302


# ─────────────────────────────────────────────────────────────────────────────
# DataDeletionCompleteView
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDataDeletionCompleteView:
    def _url(self):
        return reverse("users:deletion_complete")

    def test_accessible_without_login(self, client):
        response = client.get(self._url())
        assert response.status_code == 200

    def test_renders_success_message(self, client):
        response = client.get(self._url())
        content = response.content.decode().lower()
        assert "deleted" in content or "removed" in content

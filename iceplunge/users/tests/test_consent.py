import pytest
from django.test import RequestFactory
from django.urls import reverse

from iceplunge.users.middleware import ConsentRequiredMiddleware
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestConsentMiddleware:
    def _make_middleware(self, get_response=None):
        if get_response is None:
            get_response = lambda req: None  # noqa: E731
        return ConsentRequiredMiddleware(get_response)

    def test_unauthenticated_user_passes_through(self, client):
        """Unauthenticated users are never redirected by the middleware."""
        response = client.get(reverse("home"))
        # No redirect to consent — home returns 200 or its own redirect
        assert response.status_code != 302 or response["Location"] != reverse("users:consent")

    def test_consented_user_passes_through(self, client):
        user = UserFactory()
        ConsentProfile.objects.create(user=user, consented_at="2024-01-01T00:00:00Z")
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == 200

    def test_unconsented_user_sees_modal(self, client):
        """GET requests let through with consent modal injected rather than redirected."""
        user = UserFactory()
        ConsentProfile.objects.create(user=user, consented_at=None)
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == 200
        assert b"consentModal" in response.content

    def test_user_with_no_consent_profile_sees_modal(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == 200
        assert b"consentModal" in response.content

    def test_consent_view_is_exempt(self, client):
        """Accessing the consent view itself must not cause an infinite redirect loop."""
        user = UserFactory()
        client.force_login(user)
        response = client.get(reverse("users:consent"))
        assert response.status_code == 200

    def test_post_consent_creates_profile(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.post(reverse("users:consent"))
        assert response.status_code == 302
        profile = ConsentProfile.objects.get(user=user)
        assert profile.consented_at is not None

    def test_post_consent_updates_existing_profile(self, client):
        user = UserFactory()
        ConsentProfile.objects.create(user=user, consented_at=None)
        client.force_login(user)
        client.post(reverse("users:consent"))
        profile = ConsentProfile.objects.get(user=user)
        assert profile.consented_at is not None

    def test_outdated_consent_version_sees_modal(self, client, settings):
        """A user whose consent version is outdated sees the re-consent modal."""
        settings.CURRENT_CONSENT_VERSION = "2.0"
        user = UserFactory()
        ConsentProfile.objects.create(user=user, consented_at="2024-01-01T00:00:00Z", consent_version="1.0")
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == 200
        assert b"consentModal" in response.content
        assert b"updated" in response.content  # updated-version message shown

    def test_post_consent_saves_current_version(self, client, settings):
        """Consenting saves the current consent version from settings."""
        settings.CURRENT_CONSENT_VERSION = "2.0"
        user = UserFactory()
        client.force_login(user)
        client.post(reverse("users:consent"))
        profile = ConsentProfile.objects.get(user=user)
        assert profile.consent_version == "2.0"

    def test_my_data_exempt_from_consent_middleware(self, client):
        """my-data download is accessible even when consent is pending (Article 20)."""
        user = UserFactory()
        ConsentProfile.objects.create(user=user, consented_at=None)
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestPseudonymisedId:
    def test_pseudonymised_id_auto_generated(self):
        user = UserFactory()
        assert user.pseudonymised_id is not None

    def test_pseudonymised_id_unique(self):
        user1 = UserFactory()
        user2 = UserFactory()
        assert user1.pseudonymised_id != user2.pseudonymised_id

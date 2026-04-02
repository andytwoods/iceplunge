import json

import pytest
from django.urls import reverse

from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at="2024-01-01T00:00:00Z")
    return user


@pytest.mark.django_db
class TestMyDataExportView:
    def test_requires_login(self, client):
        response = client.get(reverse("users:my_data"))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_returns_json(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_content_disposition_is_attachment(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        assert "attachment" in response["Content-Disposition"]
        assert "my_data_" in response["Content-Disposition"]

    def test_payload_contains_account_fields(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        payload = json.loads(response.content)
        assert payload["account"]["email"] == user.email
        assert payload["account"]["name"] == user.name
        assert "pseudonymised_id" in payload["account"]
        assert "date_joined" in payload["account"]

    def test_payload_contains_consent(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        payload = json.loads(response.content)
        assert payload["consent"]["consented_at"] is not None
        assert "consent_version" in payload["consent"]

    def test_payload_contains_expected_keys(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        payload = json.loads(response.content)
        for key in ("exported_at", "account", "consent", "baseline_profile",
                    "plunge_logs", "cognitive_sessions", "daily_covariates", "weekly_covariates"):
            assert key in payload, f"Missing key: {key}"

    def test_user_only_sees_own_data(self, client):
        """Another user's data must never appear in the export."""
        user = _consented_user()
        _other = _consented_user()
        client.force_login(user)
        response = client.get(reverse("users:my_data"))
        payload = json.loads(response.content)
        assert payload["account"]["email"] == user.email

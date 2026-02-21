import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.plunges.models import PlungeLog
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    """Return a user with an active consent profile so middleware passes."""
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


def _plunge_payload(**overrides):
    data = {
        "timestamp": "2024-01-15 10:00:00",
        "duration_minutes": 5,
        "water_temp_celsius": "",
        "temp_measured": False,
        "immersion_depth": "chest",
        "context": "lake",
        "breathing_technique": "",
        "perceived_intensity": 3,
        "thermal_sensation": "",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestPlungeListView:
    def test_login_required(self, client):
        response = client.get(reverse("plunges:list"))
        assert response.status_code == 302
        assert "login" in response["Location"] or "accounts" in response["Location"]

    def test_authenticated_returns_200(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("plunges:list"))
        assert response.status_code == 200

    def test_only_own_plunges_shown(self, client):
        user = _consented_user()
        other = _consented_user()
        client.force_login(user)
        PlungeLog.objects.create(
            user=user, duration_minutes=5, immersion_depth="chest",
            context="lake", perceived_intensity=3,
        )
        PlungeLog.objects.create(
            user=other, duration_minutes=10, immersion_depth="neck",
            context="sea", perceived_intensity=5,
        )
        response = client.get(reverse("plunges:list"))
        assert response.status_code == 200
        plunges = response.context["plunges"]
        assert all(p.user == user for p in plunges)


@pytest.mark.django_db
class TestPlungeCreateView:
    def test_create_plunge_success(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(reverse("plunges:create"), data=_plunge_payload())
        assert PlungeLog.objects.filter(user=user).count() == 1
        assert response.status_code == 302

    def test_create_via_htmx_returns_partial(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.post(
            reverse("plunges:create"),
            data=_plunge_payload(),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"<tr" in response.content

    def test_create_assigns_request_user(self, client):
        user = _consented_user()
        client.force_login(user)
        client.post(reverse("plunges:create"), data=_plunge_payload())
        plunge = PlungeLog.objects.get(user=user)
        assert plunge.user == user


@pytest.mark.django_db
class TestPlungeDeleteView:
    def _create_plunge(self, user):
        return PlungeLog.objects.create(
            user=user, duration_minutes=5, immersion_depth="chest",
            context="lake", perceived_intensity=3,
        )

    def test_owner_can_delete(self, client):
        user = _consented_user()
        client.force_login(user)
        plunge = self._create_plunge(user)
        response = client.post(reverse("plunges:delete", kwargs={"pk": plunge.pk}))
        assert response.status_code == 302
        assert not PlungeLog.objects.filter(pk=plunge.pk).exists()

    def test_other_user_gets_404(self, client):
        owner = _consented_user()
        attacker = _consented_user()
        client.force_login(attacker)
        plunge = self._create_plunge(owner)
        response = client.post(reverse("plunges:delete", kwargs={"pk": plunge.pk}))
        assert response.status_code == 404
        assert PlungeLog.objects.filter(pk=plunge.pk).exists()

    def test_delete_via_htmx_returns_200(self, client):
        user = _consented_user()
        client.force_login(user)
        plunge = self._create_plunge(user)
        response = client.post(
            reverse("plunges:delete", kwargs={"pk": plunge.pk}),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert not PlungeLog.objects.filter(pk=plunge.pk).exists()


@pytest.mark.django_db
class TestPlungeUpdateView:
    def _create_plunge(self, user):
        return PlungeLog.objects.create(
            user=user,
            duration_minutes=5,
            immersion_depth="waist",
            context="bath",
            perceived_intensity=1,
        )

    def test_get_form_for_edit(self, client):
        user = _consented_user()
        client.force_login(user)
        plunge = self._create_plunge(user)
        response = client.get(
            reverse("plunges:form_edit", kwargs={"pk": plunge.pk}),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"Update plunge" in response.content
        assert b"Editing plunge from:" in response.content
        assert b"Edit plunge" in response.content
        # Check if values are in form
        assert b'value="bath"' in response.content
        assert b'value="waist"' in response.content
        assert str(plunge.duration_minutes).encode() in response.content

    def test_update_plunge_success(self, client):
        user = _consented_user()
        client.force_login(user)
        plunge = self._create_plunge(user)
        payload = _plunge_payload(duration_minutes=15, context="sea")
        response = client.post(
            reverse("plunges:update", kwargs={"pk": plunge.pk}),
            data=payload,
        )
        assert response.status_code == 302
        plunge.refresh_from_db()
        assert plunge.duration_minutes == 15
        assert plunge.context == "sea"

    def test_update_via_htmx_returns_partial(self, client):
        user = _consented_user()
        client.force_login(user)
        plunge = self._create_plunge(user)
        payload = _plunge_payload(duration_minutes=20)
        response = client.post(
            reverse("plunges:update", kwargs={"pk": plunge.pk}),
            data=payload,
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"<tr" in response.content
        assert b"20" in response.content
        assert response["HX-Retarget"] == f"#plunge-{plunge.pk}"
        assert response["HX-Reswap"] == "outerHTML"

    def test_other_user_cannot_update(self, client):
        owner = _consented_user()
        attacker = _consented_user()
        client.force_login(attacker)
        plunge = self._create_plunge(owner)
        payload = _plunge_payload(duration_minutes=25)
        response = client.post(
            reverse("plunges:update", kwargs={"pk": plunge.pk}),
            data=payload,
        )
        assert response.status_code == 404
        plunge.refresh_from_db()
        assert plunge.duration_minutes == 5

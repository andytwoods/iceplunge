import pytest
from django.urls import reverse
from django.utils import timezone

from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


@pytest.mark.django_db
class TestAppHomeView:
    def test_anonymous_redirects_to_login(self, client):
        url = reverse("app_home")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_consented_user_gets_200(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200

    def test_context_has_last_plunge(self, client):
        from iceplunge.plunges.models import PlungeLog

        user = _consented_user()
        plunge = PlungeLog.objects.create(
            user=user,
            duration_minutes=5,
            immersion_depth="chest",
            context="lake",
            perceived_intensity=3,
        )
        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200
        assert response.context["last_plunge"] == plunge

    def test_context_last_plunge_none_when_no_plunges(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200
        assert response.context["last_plunge"] is None

    def test_context_has_last_session(self, client):
        from iceplunge.tasks.helpers.session_helpers import create_session
        from iceplunge.tasks.models import CognitiveSession

        user = _consented_user()
        session = create_session(user)
        CognitiveSession.objects.filter(pk=session.pk).update(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
            completed_at=timezone.now(),
            is_practice=False,
        )
        session.refresh_from_db()

        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200
        assert response.context["last_session"] == session

    def test_context_last_session_excludes_practice(self, client):
        from iceplunge.tasks.helpers.session_helpers import create_session
        from iceplunge.tasks.models import CognitiveSession

        user = _consented_user()
        session = create_session(user)
        CognitiveSession.objects.filter(pk=session.pk).update(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
            completed_at=timezone.now(),
            is_practice=True,
        )

        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200
        assert response.context["last_session"] is None

    def test_context_has_greeting(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert response.status_code == 200
        greeting = response.context["greeting"]
        assert greeting in ("Good morning", "Good afternoon", "Good evening")

    def test_uses_app_home_template(self, client):
        user = _consented_user()
        client.force_login(user)
        response = client.get(reverse("app_home"))
        assert "app/home.html" in [t.name for t in response.templates]

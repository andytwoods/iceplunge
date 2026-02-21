"""Tests for the OneSignal integration module."""
import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from iceplunge.notifications.models import NotificationProfile
from iceplunge.notifications.onesignal import OneSignalError, register_device, send_push
from iceplunge.users.models import ConsentProfile
from iceplunge.users.tests.factories import UserFactory


def _consented_user():
    user = UserFactory()
    ConsentProfile.objects.create(user=user, consented_at=timezone.now())
    return user


@pytest.mark.django_db
class TestRegisterDevice:
    def test_creates_profile_and_stores_player_id(self):
        user = _consented_user()
        profile = register_device(user, "player-abc-123")
        assert profile.onesignal_player_id == "player-abc-123"

    def test_updates_existing_player_id(self):
        user = _consented_user()
        NotificationProfile.objects.create(user=user, onesignal_player_id="old-id")
        profile = register_device(user, "new-id")
        assert profile.onesignal_player_id == "new-id"
        assert NotificationProfile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestSendPush:
    def _make_user_with_profile(self, player_id="player-xyz"):
        user = _consented_user()
        NotificationProfile.objects.create(user=user, onesignal_player_id=player_id)
        return user

    def test_raises_onesignal_error_on_non_2xx(self):
        user = self._make_user_with_profile()
        http_error = urllib.error.HTTPError(
            url="https://onesignal.com/api/v1/notifications",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"errors":["invalid_player_id"]}'),
        )
        with patch("iceplunge.notifications.onesignal.urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(OneSignalError):
                send_push(user, "Title", "Body")

    def test_returns_response_dict_on_success(self):
        user = self._make_user_with_profile()
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": "notif-123", "recipients": 1}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("iceplunge.notifications.onesignal.urllib.request.urlopen", return_value=mock_response):
            result = send_push(user, "Title", "Body")

        assert result["id"] == "notif-123"

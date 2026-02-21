"""
OneSignal push notification integration.

Docs: https://documentation.onesignal.com/reference/rest-api-overview
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from iceplunge.notifications.models import NotificationProfile

logger = logging.getLogger(__name__)

ONESIGNAL_NOTIFICATIONS_URL = "https://onesignal.com/api/v1/notifications"


class OneSignalError(Exception):
    """Raised when OneSignal returns a non-2xx response."""


def send_push(user, title: str, body: str, data: dict | None = None) -> dict:
    """
    Send a push notification to a user's registered OneSignal device.

    Args:
        user:   The User to notify (must have a NotificationProfile with a player ID).
        title:  Notification title.
        body:   Notification body text.
        data:   Optional dict of extra key-value data sent alongside the notification.

    Returns:
        The parsed JSON response dict from OneSignal.

    Raises:
        OneSignalError: if OneSignal returns a non-2xx HTTP status.
        NotificationProfile.DoesNotExist: if the user has no NotificationProfile.
    """
    profile = NotificationProfile.objects.get(user=user)
    player_id = profile.onesignal_player_id

    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "include_player_ids": [player_id],
        "headings": {"en": title},
        "contents": {"en": body},
    }
    if data:
        payload["data"] = data

    request = urllib.request.Request(
        ONESIGNAL_NOTIFICATIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise OneSignalError(
            f"OneSignal returned HTTP {exc.code}: {error_body}"
        ) from exc


def register_device(user, onesignal_player_id: str) -> NotificationProfile:
    """
    Associate a OneSignal player ID with a user's NotificationProfile.

    Creates the NotificationProfile if one does not yet exist.
    """
    profile, _ = NotificationProfile.objects.get_or_create(user=user)
    profile.onesignal_player_id = onesignal_player_id
    profile.save(update_fields=["onesignal_player_id"])
    return profile

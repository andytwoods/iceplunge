"""
Strava API helpers: token refresh and activity fetching.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

# Keywords that identify a cold-plunge activity by name (case-insensitive).
_COLD_KEYWORDS = ("cold", "ice", "plunge", "cryo")


def get_strava_token(user):
    """Return the user's SocialToken for Strava, or None if not connected."""
    from allauth.socialaccount.models import SocialToken
    return (
        SocialToken.objects
        .select_related("account", "app")
        .filter(account__user=user, account__provider="strava")
        .first()
    )


def refresh_token_if_needed(token) -> None:
    """Refresh the Strava access token in-place if it has expired."""
    if token.expires_at and token.expires_at > timezone.now():
        return  # Still valid

    logger.info("Refreshing Strava token for account %s", token.account_id)

    resp = requests.post(
        _STRAVA_TOKEN_URL,
        data={
            "client_id": token.app.client_id,
            "client_secret": token.app.secret,
            "grant_type": "refresh_token",
            "refresh_token": token.token_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    token.token = data["access_token"]
    token.token_secret = data["refresh_token"]
    token.expires_at = datetime.fromtimestamp(data["expires_at"], tz=dt_timezone.utc)
    token.save(update_fields=["token", "token_secret", "expires_at"])


def fetch_cold_activities(token, per_page: int = 100) -> list[dict]:
    """
    Return Strava activities that look like cold plunges.

    Filters for activities whose name contains any of _COLD_KEYWORDS
    (case-insensitive).  sport_type is not restricted so users can log
    plunges as any activity type on their watch.
    """
    resp = requests.get(
        _STRAVA_ACTIVITIES_URL,
        headers={"Authorization": f"Bearer {token.token}"},
        params={"per_page": per_page},
        timeout=15,
    )
    resp.raise_for_status()
    activities = resp.json()

    return [
        a for a in activities
        if any(kw in a.get("name", "").lower() for kw in _COLD_KEYWORDS)
    ]


def import_cold_activities(user, token) -> int:
    """
    Fetch cold activities from Strava and create PlungeLog records for any
    that haven't been imported yet.  Returns the count of newly created logs.
    """
    from iceplunge.plunges.models import PlungeLog

    refresh_token_if_needed(token)
    activities = fetch_cold_activities(token)

    # Only process IDs not already in the DB
    existing_ids = set(
        PlungeLog.objects.filter(
            user=user,
            strava_activity_id__in=[a["id"] for a in activities],
        ).values_list("strava_activity_id", flat=True)
    )

    imported = 0
    for activity in activities:
        if activity["id"] in existing_ids:
            continue

        # Parse start_date_local (Strava returns it as "2024-01-15T10:30:00Z"
        # but the value is already in the athlete's local timezone — treat it
        # as UTC-naive and make it timezone-aware).
        raw_dt = activity.get("start_date_local", activity.get("start_date", ""))
        try:
            naive = datetime.strptime(raw_dt.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
            ts = timezone.make_aware(naive)
        except (ValueError, AttributeError):
            ts = timezone.now()

        duration_minutes = max(1, round(activity.get("elapsed_time", 60) / 60))

        PlungeLog.objects.create(
            user=user,
            timestamp=ts,
            duration_minutes=duration_minutes,
            # Sensible defaults — user can edit afterwards
            immersion_depth=PlungeLog.ImmersionDepth.CHEST,
            context=PlungeLog.Context.OTHER,
            perceived_intensity=3,
            strava_activity_id=activity["id"],
        )
        imported += 1

    return imported

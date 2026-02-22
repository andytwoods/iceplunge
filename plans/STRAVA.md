# Strava Integration Plan

## Goal

Auto-import cold plunge activities from Strava into the plunge log, reducing manual entry friction. The user logs plunges on their Garmin watch as "Other" activities with "cold" in the title, which sync to Strava.

## Background

- Garmin has no open official API — requires partner approval via the Garmin Health API.
- Strava has a public OAuth API anyone can register for, and most Garmin users already sync to Strava.
- Strava exposes `average_temp` but this is **ambient air temperature**, not water temperature. Water temp is lost in the Garmin → Strava transit and must still be entered manually.
- `django-allauth` is already installed with social providers (Google, GitHub), so adding Strava is minimal work.

## What gets auto-filled

| Strava field | PlungeLog field | Notes |
|---|---|---|
| `start_date_local` | `timestamp` | ✅ exact |
| `elapsed_time` ÷ 60 | `duration_minutes` | ✅ |
| `average_heartrate` | (new field) | useful research covariate |
| `average_temp` | — | ambient air only, skip |
| `name` | — | used for filtering only |

Fields still entered manually: water temperature, depth, setting, perceived intensity, head submerged, hot treatment, exercise.

## Implementation steps

### 1. Enable the allauth Strava provider
- Add `allauth.socialaccount.providers.strava` to `INSTALLED_APPS` in `config/settings/base.py`.
- Register an OAuth app at strava.com/settings/api (callback URL: `/accounts/strava/login/callback/`).
- Add `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` to environment / secrets.
- Run `migrate` (allauth creates the social account tables automatically).

### 2. Add `strava_activity_id` to `PlungeLog`
- New optional field `strava_activity_id = BigIntegerField(null=True, blank=True, unique=True)` to track which Strava activities have already been imported and prevent duplicates.

### 3. Add `StravaSyncView`
```python
# iceplunge/plunges/views.py
from allauth.socialaccount.models import SocialToken
import requests

class StravaSyncView(LoginRequiredMixin, View):
    def post(self, request):
        token = SocialToken.objects.get(
            account__user=request.user,
            account__provider="strava"
        )
        activities = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token.token}"},
            params={"per_page": 100}
        ).json()

        cold = [
            a for a in activities
            if a["sport_type"] == "Other"
            and "cold" in a["name"].lower()
            and not PlungeLog.objects.filter(strava_activity_id=a["id"]).exists()
        ]
        # Create draft PlungeLogs or pre-populate modal
```

- Add URL: `path("strava/sync/", view=strava_sync_view, name="strava_sync")`

### 4. UI

- **User profile page**: "Connect Strava" button (allauth social connect flow).
- **Plunge list page**: "Import from Strava" button — calls `StravaSyncView`, creates draft entries or opens the log modal pre-populated with imported data.

### 5. Token refresh
Strava access tokens expire after 6 hours. allauth stores the refresh token in `SocialToken.token_secret`. Before each API call, check expiry and refresh if needed using `https://www.strava.com/oauth/token`.

## Open questions

- Should imports create draft `PlungeLog` entries (user reviews before saving) or open the modal pre-populated?
- Should there be a webhook for real-time push from Strava, or is a manual "sync" button sufficient to start?
- Add `average_heartrate` as a new field to `PlungeLog` or keep it in covariates?

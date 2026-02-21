import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from iceplunge.notifications.models import NotificationProfile
from iceplunge.notifications.onesignal import register_device


class RegisterDeviceView(LoginRequiredMixin, View):
    """
    Receives a OneSignal player ID from the Capacitor JS layer and stores it
    on the user's NotificationProfile.

    POST body (JSON): { "player_id": "<onesignal_player_id>" }
    Returns: 200 { "ok": true } | 422 on missing field
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        player_id = data.get("player_id")
        if not player_id:
            return JsonResponse({"error": "player_id is required"}, status=422)

        register_device(request.user, player_id)
        return JsonResponse({"ok": True})


class NotificationPreferencesView(LoginRequiredMixin, View):
    """
    GET  — render form showing current push_enabled, morning_window_start, evening_window_start.
    POST — update NotificationProfile; HTMX-aware.
    """

    template_name = "notifications/preferences.html"
    partial_template_name = "notifications/partials/_notification_prefs.html"

    def _get_or_create_profile(self, user):
        profile, _ = NotificationProfile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        from iceplunge.notifications.forms import NotificationPreferencesForm

        profile = self._get_or_create_profile(request.user)
        form = NotificationPreferencesForm(instance=profile)
        template = (
            self.partial_template_name
            if request.headers.get("HX-Request")
            else self.template_name
        )
        return render(request, template, {"form": form, "profile": profile})

    def post(self, request):
        from iceplunge.notifications.forms import NotificationPreferencesForm

        profile = self._get_or_create_profile(request.user)
        form = NotificationPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    self.partial_template_name,
                    {"form": form, "profile": profile, "saved": True},
                )
            return redirect("notifications:preferences")
        template = (
            self.partial_template_name
            if request.headers.get("HX-Request")
            else self.template_name
        )
        return render(request, template, {"form": form, "profile": profile})


register_device_view = RegisterDeviceView.as_view()
notification_preferences_view = NotificationPreferencesView.as_view()

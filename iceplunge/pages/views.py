from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Sponsor


class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_template_names(self):
        if self.request.user.is_authenticated:
            return ["pages/member_home.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            return self._member_context(context)
        sponsors = Sponsor.objects.filter(is_active=True)
        context["org_sponsors"] = sponsors.filter(tier=Sponsor.TIER_ORGANISATION)
        context["individual_sponsors"] = sponsors.filter(tier=Sponsor.TIER_INDIVIDUAL)
        return context

    def _member_context(self, context):
        from iceplunge.plunges.models import PlungeLog
        from iceplunge.tasks.models import CognitiveSession

        user = self.request.user
        context["plunge_count"] = PlungeLog.objects.filter(user=user).count()
        context["session_count"] = CognitiveSession.objects.filter(
            user=user,
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
            is_practice=False,
        ).count()
        context["last_plunge"] = (
            PlungeLog.objects.filter(user=user).order_by("-timestamp").first()
        )
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "pages/settings.html"

    def get_context_data(self, **kwargs):
        from iceplunge.notifications.forms import NotificationPreferencesForm
        from iceplunge.notifications.models import NotificationProfile
        from iceplunge.tasks.models import TaskConfig, UserTaskPreference
        from iceplunge.tasks.registry import TASK_REGISTRY

        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Task preferences
        globally_enabled = set(
            TaskConfig.objects.filter(is_enabled=True).values_list("task_type", flat=True)
        )
        try:
            pref = UserTaskPreference.objects.get(user=user)
            user_disabled = set(pref.disabled_task_types)
        except UserTaskPreference.DoesNotExist:
            user_disabled = set()
        context["task_list"] = [
            {
                "type": t,
                "label": meta["label"],
                "duration_display": meta["duration_display"],
                "instructions": meta["instructions"],
                "is_enabled": t not in user_disabled,
            }
            for t, meta in TASK_REGISTRY.items()
            if t in globally_enabled
        ]

        # Notification preferences
        profile, _ = NotificationProfile.objects.get_or_create(user=user)
        context["notif_form"] = NotificationPreferencesForm(instance=profile)
        context["notif_profile"] = profile

        return context


class AppHomeView(LoginRequiredMixin, TemplateView):
    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        from datetime import datetime

        from iceplunge.plunges.models import PlungeLog
        from iceplunge.tasks.models import CognitiveSession

        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["last_plunge"] = (
            PlungeLog.objects.filter(user=user).order_by("-timestamp").first()
        )
        context["last_session"] = (
            CognitiveSession.objects.filter(
                user=user,
                completion_status=CognitiveSession.CompletionStatus.COMPLETE,
                is_practice=False,
            )
            .order_by("-completed_at")
            .first()
        )
        hour = datetime.now().hour
        if hour < 12:
            context["greeting"] = "Good morning"
        elif hour < 18:
            context["greeting"] = "Good afternoon"
        else:
            context["greeting"] = "Good evening"
        return context

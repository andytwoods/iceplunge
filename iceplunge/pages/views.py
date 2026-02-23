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

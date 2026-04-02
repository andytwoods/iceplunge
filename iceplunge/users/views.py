import json

from allauth.account.views import SignupView
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django_ratelimit.decorators import ratelimit

from iceplunge.users.forms import BaselineProfileForm
from iceplunge.users.models import BaselineProfile
from iceplunge.users.models import ConsentProfile

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None=None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


class ConsentView(LoginRequiredMixin, TemplateView):
    template_name = "users/consent.html"

    def post(self, request, *args, **kwargs):
        profile, _ = ConsentProfile.objects.get_or_create(user=request.user)
        profile.consented_at = timezone.now()
        profile.consent_version = getattr(settings, "CURRENT_CONSENT_VERSION", "1.0")
        profile.save(update_fields=["consented_at", "consent_version"])
        return redirect(reverse("home"))


consent_view = ConsentView.as_view()


class BaselineProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Shown after consent for first-time completion; also used in profile settings."""

    form_class = BaselineProfileForm
    template_name = "users/baseline_profile.html"
    success_message = _("Profile saved successfully")

    def get_object(self, queryset=None):
        profile, _ = BaselineProfile.objects.get_or_create(
            user=self.request.user,
            defaults={"age": 0, "gender": "", "height_cm": 0, "weight_kg": 0,
                      "handedness": "right", "plunge_years": 0},
        )
        return profile

    def get_success_url(self) -> str:
        return reverse("home")


baseline_profile_view = BaselineProfileView.as_view()


class DataDeletionView(LoginRequiredMixin, View):
    """
    T10.1 — Self-service data deletion.

    GET  — render a confirmation page explaining what will be deleted.
    POST — validate the "confirm" checkbox, delete all user data (cascade),
           send a confirmation email to the address on record, then log out.
    """

    template_name = "users/data_deletion.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        if request.POST.get("confirm") != "yes":
            return render(request, self.template_name, {"error": True})

        user = request.user
        email = user.email

        # Cascade-delete all linked records including the user account itself
        user.delete()

        logout(request)

        # Best-effort confirmation email — fail_silently suppresses backend errors
        send_mail(
            subject="Your data has been deleted",
            message=(
                "Your account and all associated data have been permanently deleted "
                "from the Ice Plunge research platform.\n\n"
                "If you did not request this, please contact the research team immediately.\n\n"
                "Thank you for your participation."
            ),
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[email],
            fail_silently=True,
        )

        return redirect(reverse("users:deletion_complete"))


class DataDeletionCompleteView(TemplateView):
    """Shown after successful account and data deletion (unauthenticated)."""

    template_name = "users/data_deletion_complete.html"


data_deletion_view = DataDeletionView.as_view()
data_deletion_complete_view = DataDeletionCompleteView.as_view()


class MyDataExportView(LoginRequiredMixin, View):
    """
    Article 20 UK GDPR — Right to data portability.

    Returns all personal data held for the authenticated user as a
    machine-readable JSON file.  Always accessible regardless of consent
    version so users can retrieve their data even before re-consenting.
    """

    def get(self, request):
        from iceplunge.covariates.models import DailyCovariate, WeeklyCovariate
        from iceplunge.plunges.models import PlungeLog
        from iceplunge.tasks.models import CognitiveSession

        user = request.user

        baseline = None
        if hasattr(user, "baseline_profile"):
            bp = user.baseline_profile
            baseline = {
                "age": bp.age,
                "gender": bp.gender,
                "height_cm": str(bp.height_cm),
                "weight_kg": str(bp.weight_kg),
                "bmi": str(bp.bmi),
                "handedness": bp.handedness,
                "plunge_years": str(bp.plunge_years),
            }

        consent = None
        if hasattr(user, "consent_profile"):
            cp = user.consent_profile
            consent = {
                "consented_at": cp.consented_at.isoformat() if cp.consented_at else None,
                "consent_version": cp.consent_version,
            }

        plunge_logs = [
            {
                "id": pl.id,
                "timestamp": pl.timestamp.isoformat(),
                "duration_minutes": pl.duration_minutes,
                "water_temp_celsius": str(pl.water_temp_celsius) if pl.water_temp_celsius is not None else None,
                "temp_measured": pl.temp_measured,
                "immersion_depth": pl.immersion_depth,
                "context": pl.context,
                "breathing_technique": pl.breathing_technique,
                "perceived_intensity": pl.perceived_intensity,
                "head_submerged": pl.head_submerged,
                "pre_hot_treatment": pl.pre_hot_treatment,
                "pre_hot_treatment_minutes": pl.pre_hot_treatment_minutes,
                "exercise_timing": pl.exercise_timing,
                "exercise_type": pl.exercise_type,
                "exercise_minutes": pl.exercise_minutes,
            }
            for pl in PlungeLog.objects.filter(user=user).order_by("timestamp")
        ]

        cognitive_sessions = [
            {
                "id": str(cs.id),
                "started_at": cs.started_at.isoformat() if cs.started_at else None,
                "completed_at": cs.completed_at.isoformat() if cs.completed_at else None,
                "completion_status": cs.completion_status,
                "is_practice": cs.is_practice,
                "quality_flags": cs.quality_flags or [],
                "task_order": cs.task_order or [],
                "device_meta": cs.device_meta,
            }
            for cs in CognitiveSession.objects.filter(user=user).order_by("started_at")
        ]

        daily_covariates = [
            {
                "date": str(dc.date),
                "sleep_duration_hours": str(dc.sleep_duration_hours) if dc.sleep_duration_hours is not None else None,
                "sleep_quality": dc.sleep_quality,
                "alcohol_last_24h": dc.alcohol_last_24h,
                "exercise_today": dc.exercise_today,
                "menstruation_today": dc.menstruation_today,
            }
            for dc in DailyCovariate.objects.filter(user=user).order_by("date")
        ]

        weekly_covariates = [
            {
                "week_start": str(wc.week_start),
                "gi_severity": wc.gi_severity,
                "gi_symptoms": wc.gi_symptoms,
                "illness_status": wc.illness_status,
            }
            for wc in WeeklyCovariate.objects.filter(user=user).order_by("week_start")
        ]

        payload = {
            "exported_at": timezone.now().isoformat(),
            "account": {
                "email": user.email,
                "name": user.name,
                "date_joined": user.date_joined.isoformat(),
                "pseudonymised_id": str(user.pseudonymised_id),
            },
            "consent": consent,
            "baseline_profile": baseline,
            "plunge_logs": plunge_logs,
            "cognitive_sessions": cognitive_sessions,
            "daily_covariates": daily_covariates,
            "weekly_covariates": weekly_covariates,
        }

        response = HttpResponse(
            json.dumps(payload, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="my_data_{timezone.now().date().isoformat()}.json"'
        )
        return response


my_data_export_view = MyDataExportView.as_view()


@method_decorator(
    ratelimit(key="ip", rate="10/h", method="POST", block=False),
    name="dispatch",
)
class RateLimitedSignupView(SignupView):
    """
    Wraps allauth's SignupView with an IP-based rate limit of 10 POST
    attempts per hour. Returns 429 with a user-friendly page when exceeded.
    """

    def dispatch(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return render(request, "account/signup_ratelimited.html", status=429)
        return super().dispatch(request, *args, **kwargs)


rate_limited_signup_view = RateLimitedSignupView.as_view()

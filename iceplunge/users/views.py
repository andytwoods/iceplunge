from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

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
        profile.save(update_fields=["consented_at"])
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

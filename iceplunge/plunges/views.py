import datetime
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from iceplunge.covariates.forms import DailyCovariateForm
from iceplunge.covariates.forms import WeeklyCovariateForm
from iceplunge.covariates.models import DailyCovariate
from iceplunge.covariates.models import WeeklyCovariate

from .forms import PlungeLogForm
from .models import PlungeLog


def _covariate_instances(user):
    """Return (daily_instance, weekly_instance) for today, creating if needed."""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    daily, _ = DailyCovariate.objects.get_or_create(user=user, date=today)
    weekly, _ = WeeklyCovariate.objects.get_or_create(user=user, week_start=week_start)
    return daily, weekly


class PlungeListView(LoginRequiredMixin, ListView):
    template_name = "plunges/plunge_list.html"
    context_object_name = "plunges"
    paginate_by = 20

    def get_queryset(self):
        return PlungeLog.objects.filter(user=self.request.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)


plunge_list_view = PlungeListView.as_view()


class PlungeFormView(LoginRequiredMixin, View):
    """Return the plunge log form partial via HTMX GET."""

    def get(self, request):
        if not request.headers.get("HX-Request"):
            return redirect(reverse("plunges:list"))
        return HttpResponse(
            _render_form_partial(request),
            content_type="text/html",
        )


plunge_form_view = PlungeFormView.as_view()


class PlungeCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect(reverse("plunges:list"))

    def post(self, request):
        form = PlungeLogForm(request.POST)
        daily, weekly = _covariate_instances(request.user)
        daily_form = DailyCovariateForm(request.POST, instance=daily)
        weekly_form = WeeklyCovariateForm(request.POST, instance=weekly)

        if form.is_valid():
            plunge = form.save(commit=False)
            plunge.user = request.user
            plunge.save()
            if daily_form.is_valid():
                daily_form.save()
            if weekly_form.is_valid():
                weekly_form.save()
            if request.headers.get("HX-Request"):
                row_html = _render_plunge_row(request, plunge)
                response = HttpResponse(row_html, content_type="text/html")
                response["HX-Retarget"] = "#plunge-list-body"
                response["HX-Reswap"] = "afterbegin"
                response["HX-Trigger"] = json.dumps(
                    {"plungeLogged": {"message": "Plunge logged!", "type": "success"}}
                )
                return response
            return redirect(reverse("plunges:list"))

        if request.headers.get("HX-Request"):
            return HttpResponse(
                _render_form_partial(request, form, daily_form, weekly_form),
                content_type="text/html",
                status=422,
            )
        return redirect(reverse("plunges:list"))


plunge_create_view = PlungeCreateView.as_view()


class PlungeDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        plunge = get_object_or_404(PlungeLog, pk=pk, user=request.user)
        plunge.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse(status=200)
        return redirect(reverse("plunges:list"))


plunge_delete_view = PlungeDeleteView.as_view()


# ---------------------------------------------------------------------------
# Private helpers — render partials without importing template machinery
# at module load time.
# ---------------------------------------------------------------------------

def _render_plunge_row(request, plunge):
    from django.template.loader import render_to_string
    return render_to_string("plunges/partials/_plunge_row.html", {"plunge": plunge}, request=request)


def _build_plunge_form(user):
    """Return a PlungeLogForm pre-populated from the user's last plunge."""
    last = PlungeLog.objects.filter(user=user).order_by("-timestamp").first()
    initial = {"timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")}
    if last:
        initial.update({
            "duration_minutes": last.duration_minutes,
            "water_temp_celsius": last.water_temp_celsius,
            "temp_measured": last.temp_measured,
            "immersion_depth": last.immersion_depth,
            "context": last.context,
            "perceived_intensity": last.perceived_intensity,
            "head_submerged": last.head_submerged,
            "breathing_technique": last.breathing_technique,
            "pre_hot_treatment": last.pre_hot_treatment or "",
            "pre_hot_treatment_minutes": last.pre_hot_treatment_minutes,
            "exercise_timing": last.exercise_timing or "",
            "exercise_type": last.exercise_type or "",
            "exercise_minutes": last.exercise_minutes,
        })
    return PlungeLogForm(initial=initial)


def _render_form_partial(request, form=None, daily_form=None, weekly_form=None):
    from django.template.loader import render_to_string
    if form is None:
        form = _build_plunge_form(request.user)
    if daily_form is None or weekly_form is None:
        daily, weekly = _covariate_instances(request.user)
        daily_form = daily_form or DailyCovariateForm(instance=daily)
        weekly_form = weekly_form or WeeklyCovariateForm(instance=weekly)
    return render_to_string(
        "plunges/partials/_plunge_form.html",
        {
            "form": form,
            "intensity_choices": [
                (val, label, desc)
                for (val, label), desc in zip(PlungeLog.INTENSITY_CHOICES, PlungeLog.INTENSITY_DESCRIPTIONS)
            ],
            "daily_form": daily_form,
            "weekly_form": weekly_form,
        },
        request=request,
    )

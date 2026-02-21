import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from .forms import DailyCovariateForm
from .forms import WeeklyCovariateForm
from .models import DailyCovariate
from .models import WeeklyCovariate


def _get_week_start(today: datetime.date) -> datetime.date:
    return today - datetime.timedelta(days=today.weekday())


class DailyCovariateView(LoginRequiredMixin, View):
    """Create or update today's DailyCovariate for the logged-in user."""

    template_partial = "covariates/partials/_daily_form.html"

    def _get_today(self):
        return datetime.date.today()

    def get(self, request):
        today = self._get_today()
        instance, _ = DailyCovariate.objects.get_or_create(user=request.user, date=today)
        form = DailyCovariateForm(instance=instance)
        if request.headers.get("HX-Request"):
            html = render_to_string(self.template_partial, {"form": form}, request=request)
            return HttpResponse(html)
        return redirect(reverse("covariates:daily"))

    def post(self, request):
        today = self._get_today()
        instance, _ = DailyCovariate.objects.get_or_create(user=request.user, date=today)
        form = DailyCovariateForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                html = render_to_string(
                    "covariates/partials/_daily_success.html", {}, request=request
                )
                return HttpResponse(html)
            return redirect(reverse("home"))
        if request.headers.get("HX-Request"):
            html = render_to_string(self.template_partial, {"form": form}, request=request)
            return HttpResponse(html, status=422)
        return redirect(reverse("covariates:daily"))


daily_covariate_view = DailyCovariateView.as_view()


class WeeklyCovariateView(LoginRequiredMixin, View):
    """Create or update the current week's WeeklyCovariate for the logged-in user."""

    template_partial = "covariates/partials/_weekly_form.html"

    def _get_week_start(self):
        today = datetime.date.today()
        return _get_week_start(today)

    def get(self, request):
        week_start = self._get_week_start()
        instance, _ = WeeklyCovariate.objects.get_or_create(user=request.user, week_start=week_start)
        form = WeeklyCovariateForm(instance=instance)
        if request.headers.get("HX-Request"):
            html = render_to_string(self.template_partial, {"form": form}, request=request)
            return HttpResponse(html)
        return redirect(reverse("covariates:weekly"))

    def post(self, request):
        week_start = self._get_week_start()
        instance, _ = WeeklyCovariate.objects.get_or_create(user=request.user, week_start=week_start)
        form = WeeklyCovariateForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                html = render_to_string(
                    "covariates/partials/_weekly_success.html", {}, request=request
                )
                return HttpResponse(html)
            return redirect(reverse("home"))
        if request.headers.get("HX-Request"):
            html = render_to_string(self.template_partial, {"form": form}, request=request)
            return HttpResponse(html, status=422)
        return redirect(reverse("covariates:weekly"))


weekly_covariate_view = WeeklyCovariateView.as_view()


class MoreInfoView(LoginRequiredMixin, View):
    """Combined daily + weekly covariate form, reusable across the site."""

    template_partial = "covariates/partials/_more_info.html"

    def _get_today(self):
        return datetime.date.today()

    def get(self, request):
        today = self._get_today()
        week_start = _get_week_start(today)
        daily, _ = DailyCovariate.objects.get_or_create(user=request.user, date=today)
        weekly, _ = WeeklyCovariate.objects.get_or_create(user=request.user, week_start=week_start)
        daily_form = DailyCovariateForm(instance=daily)
        weekly_form = WeeklyCovariateForm(instance=weekly)
        ctx = {"daily_form": daily_form, "weekly_form": weekly_form}
        if request.headers.get("HX-Request"):
            return HttpResponse(render_to_string(self.template_partial, ctx, request=request))
        return redirect(reverse("covariates:more_info"))

    def post(self, request):
        today = self._get_today()
        week_start = _get_week_start(today)
        daily, _ = DailyCovariate.objects.get_or_create(user=request.user, date=today)
        weekly, _ = WeeklyCovariate.objects.get_or_create(user=request.user, week_start=week_start)
        daily_form = DailyCovariateForm(request.POST, instance=daily)
        weekly_form = WeeklyCovariateForm(request.POST, instance=weekly)
        if daily_form.is_valid() and weekly_form.is_valid():
            daily_form.save()
            weekly_form.save()
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    render_to_string(
                        "covariates/partials/_more_info_success.html", {}, request=request
                    )
                )
            return redirect(reverse("home"))
        ctx = {"daily_form": daily_form, "weekly_form": weekly_form}
        if request.headers.get("HX-Request"):
            return HttpResponse(
                render_to_string(self.template_partial, ctx, request=request), status=422
            )
        return redirect(reverse("covariates:more_info"))


more_info_view = MoreInfoView.as_view()

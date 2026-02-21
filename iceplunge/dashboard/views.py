"""Participant dashboard views."""
import statistics

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from iceplunge.tasks.models import CognitiveSession, MoodRating, TaskResult


class DashboardView(LoginRequiredMixin, View):
    """Renders the participant dashboard page."""

    def get(self, request):
        user = request.user
        session_count = CognitiveSession.objects.filter(
            user=user,
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
        ).count()
        return render(request, "dashboard/dashboard.html", {"session_count": session_count})


class ChartDataView(LoginRequiredMixin, View):
    """
    JSON API: returns aggregated chart data for the participant dashboard.

    Returns:
        200 {
            "rt_trend":   [{"date": "YYYY-MM-DD", "median_rt": <float|null>, "lapse_count": <int>}, ...],
            "mood_trend":  [{"date": "YYYY-MM-DD", "valence": <int>, "arousal": <int>,
                             "stress": <int>, "sharpness": <int>}, ...],
        }
    """

    def get(self, request):
        user = request.user
        rt_trend = self._rt_trend(user)
        mood_trend = self._mood_trend(user)
        return JsonResponse({"rt_trend": rt_trend, "mood_trend": mood_trend})

    # ─── helpers ──────────────────────────────────────────────────────────────

    def _rt_trend(self, user):
        """PVT median_rt + lapse_count grouped by calendar date (UTC)."""
        pvt_results = (
            TaskResult.objects.filter(
                session__user=user,
                task_type="pvt",
                is_partial=False,
            )
            .select_related("session")
            .order_by("completed_at")
        )

        points = []
        for result in pvt_results:
            date_str = result.completed_at.date().isoformat() if result.completed_at else None
            if date_str is None:
                continue
            metrics = result.summary_metrics or {}
            points.append(
                {
                    "date": date_str,
                    "median_rt": metrics.get("median_rt"),
                    "lapse_count": metrics.get("lapse_count", 0),
                }
            )
        return points

    def _mood_trend(self, user):
        """MoodRating data grouped by calendar date."""
        ratings = (
            MoodRating.objects.filter(session__user=user)
            .select_related("session")
            .order_by("session__completed_at")
        )

        points = []
        for rating in ratings:
            date_str = (
                rating.session.completed_at.date().isoformat()
                if rating.session.completed_at
                else None
            )
            if date_str is None:
                continue
            points.append(
                {
                    "date": date_str,
                    "valence": rating.valence,
                    "arousal": rating.arousal,
                    "stress": rating.stress,
                    "sharpness": rating.sharpness,
                }
            )
        return points


dashboard_view = DashboardView.as_view()
chart_data_view = ChartDataView.as_view()

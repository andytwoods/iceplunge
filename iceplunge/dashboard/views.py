"""Participant dashboard views."""
import bisect
import statistics

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from iceplunge.plunges.models import PlungeLog
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
        plunge_relative = self._plunge_relative_data(user)
        return JsonResponse({"rt_trend": rt_trend, "mood_trend": mood_trend, "plunge_relative": plunge_relative})

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


    def _plunge_relative_data(self, user):
        """
        For each session that has both a PVT result and a mood rating, find the
        most recent prior plunge and compute hours elapsed since it.

        Two queries: one for plunge timestamps, one for sessions+results+ratings.
        """
        plunge_times = list(
            PlungeLog.objects.filter(user=user)
            .order_by("timestamp")
            .values_list("timestamp", flat=True)
        )
        if not plunge_times:
            return []

        # Build a lookup: session_id -> PVT metrics
        pvt_by_session = {}
        for result in TaskResult.objects.filter(
            session__user=user, task_type="pvt", is_partial=False
        ).select_related("session"):
            pvt_by_session[result.session_id] = result.summary_metrics or {}

        # Build a lookup: session_id -> mood
        mood_by_session = {}
        for rating in MoodRating.objects.filter(session__user=user).select_related("session"):
            mood_by_session[rating.session_id] = rating

        points = []
        for session_id, metrics in pvt_by_session.items():
            mood = mood_by_session.get(session_id)
            session_time = None
            # Retrieve started_at via the already-fetched related session
            try:
                session = CognitiveSession.objects.only("started_at").get(pk=session_id)
                session_time = session.started_at
            except CognitiveSession.DoesNotExist:
                continue

            if session_time is None:
                continue

            # Binary search for the latest plunge strictly before this session
            idx = bisect.bisect_left(plunge_times, session_time) - 1
            if idx < 0:
                continue  # no plunge before this session

            hours_since = (session_time - plunge_times[idx]).total_seconds() / 3600

            point = {
                "hours_since_plunge": round(hours_since, 1),
                "median_rt": metrics.get("median_rt"),
                "lapse_count": metrics.get("lapse_count", 0),
            }
            if mood:
                point.update({
                    "valence": mood.valence,
                    "arousal": mood.arousal,
                    "stress": mood.stress,
                    "sharpness": mood.sharpness,
                })
            points.append(point)

        points.sort(key=lambda p: p["hours_since_plunge"])
        return points


dashboard_view = DashboardView.as_view()
chart_data_view = ChartDataView.as_view()

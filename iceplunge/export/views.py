"""Research data export views.

Access restricted to superusers and staff with the ``export_data`` permission.
All exports use the pseudonymised participant ID (user.id as UUID), never PII.
Export events are logged to the standard Python logger.
"""
import csv
import io
import json
import logging
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View

from iceplunge.tasks.models import CognitiveSession, TaskResult

logger = logging.getLogger(__name__)


class ExportAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow access only to superusers or staff with export_data permission."""

    def test_func(self):
        user = self.request.user
        return user.is_superuser or (user.is_staff and user.has_perm("auth.export_data"))


def _pseudo_id(user):
    """Return a stable pseudonymised identifier (user PK) with no PII."""
    return str(user.id)


# ─────────────────────────────────────────────────────────────────────────────
# T9.1 — Session-level CSV
# ─────────────────────────────────────────────────────────────────────────────


class SessionCsvExportView(ExportAccessMixin, View):
    """
    One row per CognitiveSession.  Includes covariates, derived variables,
    and per-task summary metrics flattened into columns.

    Query params:
        from_date  YYYY-MM-DD  inclusive lower bound on session started_at
        to_date    YYYY-MM-DD  inclusive upper bound on session started_at
    """

    def get(self, request):
        qs = self._filtered_qs(request)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self._header())
        for session in qs.select_related("user", "prompt_event"):
            writer.writerow(self._row(session))
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="sessions_{timezone.now().date().isoformat()}.csv"'
        )
        logger.info(
            "Session CSV export by user=%s rows=%d", request.user.pk, qs.count()
        )
        return response

    def _filtered_qs(self, request):
        qs = CognitiveSession.objects.filter(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE
        ).order_by("started_at")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        if from_date:
            qs = qs.filter(started_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(started_at__date__lte=to_date)
        return qs

    def _header(self):
        return [
            "participant_id",
            "session_id",
            "started_at_utc",
            "completed_at_utc",
            "is_practice",
            "quality_flags",
            "task_order",
            "prompt_type",
        ]

    def _row(self, session):
        prompt_type = (
            session.prompt_event.prompt_type if session.prompt_event_id else "voluntary"
        )
        return [
            _pseudo_id(session.user),
            str(session.id),
            session.started_at.isoformat() if session.started_at else "",
            session.completed_at.isoformat() if session.completed_at else "",
            session.is_practice,
            "|".join(session.quality_flags or []),
            "|".join(session.task_order or []),
            prompt_type,
        ]


# ─────────────────────────────────────────────────────────────────────────────
# T9.2 — Trial-level CSV
# ─────────────────────────────────────────────────────────────────────────────


class TrialCsvExportView(ExportAccessMixin, View):
    """
    One row per stimulus/response trial across all TaskResults.

    Query params: from_date, to_date (same semantics as SessionCsvExportView)
    """

    _TRIAL_COLUMNS = [
        "trial_index",
        "stimulus_at_ms",
        "response_at_ms",
        "rt_ms",
        "correct",
        "is_anticipation",
        "responded",
        "condition",
    ]

    def get(self, request):
        qs = self._filtered_qs(request)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self._header())
        row_count = 0
        for result in qs.select_related("session__user"):
            for trial in result.trial_data or []:
                writer.writerow(self._row(result, trial))
                row_count += 1
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="trials_{timezone.now().date().isoformat()}.csv"'
        )
        logger.info(
            "Trial CSV export by user=%s rows=%d", request.user.pk, row_count
        )
        return response

    def _filtered_qs(self, request):
        qs = TaskResult.objects.filter(is_partial=False).order_by(
            "session__started_at", "started_at"
        )
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        if from_date:
            qs = qs.filter(session__started_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(session__started_at__date__lte=to_date)
        return qs

    def _header(self):
        return [
            "participant_id",
            "session_id",
            "task_result_id",
            "task_type",
            "session_index_overall",
            "session_index_per_task",
            *self._TRIAL_COLUMNS,
        ]

    def _row(self, result, trial):
        return [
            _pseudo_id(result.session.user),
            str(result.session_id),
            str(result.id),
            result.task_type,
            result.session_index_overall,
            result.session_index_per_task,
            *[trial.get(col, "") for col in self._TRIAL_COLUMNS],
        ]


# ─────────────────────────────────────────────────────────────────────────────
# T9.2 — Full JSON dump
# ─────────────────────────────────────────────────────────────────────────────


class FullJsonExportView(ExportAccessMixin, View):
    """
    Complete nested export: sessions → task results → trials.

    Query params: from_date, to_date
    """

    def get(self, request):
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        session_qs = CognitiveSession.objects.filter(
            completion_status=CognitiveSession.CompletionStatus.COMPLETE,
        ).select_related("user", "prompt_event").order_by("started_at")

        if from_date:
            session_qs = session_qs.filter(started_at__date__gte=from_date)
        if to_date:
            session_qs = session_qs.filter(started_at__date__lte=to_date)

        result_qs = (
            TaskResult.objects.filter(
                session__in=session_qs, is_partial=False
            )
            .order_by("started_at")
        )

        results_by_session = {}
        for r in result_qs:
            results_by_session.setdefault(str(r.session_id), []).append(r)

        payload = []
        for session in session_qs:
            task_results = []
            for r in results_by_session.get(str(session.id), []):
                task_results.append(
                    {
                        "id": str(r.id),
                        "task_type": r.task_type,
                        "task_version": r.task_version,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                        "session_index_overall": r.session_index_overall,
                        "session_index_per_task": r.session_index_per_task,
                        "summary_metrics": r.summary_metrics,
                        "trials": r.trial_data,
                    }
                )
            payload.append(
                {
                    "participant_id": _pseudo_id(session.user),
                    "session_id": str(session.id),
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                    "is_practice": session.is_practice,
                    "quality_flags": session.quality_flags or [],
                    "task_order": session.task_order or [],
                    "task_results": task_results,
                }
            )

        logger.info(
            "Full JSON export by user=%s sessions=%d", request.user.pk, len(payload)
        )
        response = HttpResponse(
            json.dumps(payload, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="export_{timezone.now().date().isoformat()}.json"'
        )
        return response


session_csv_export_view = SessionCsvExportView.as_view()
trial_csv_export_view = TrialCsvExportView.as_view()
full_json_export_view = FullJsonExportView.as_view()

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from iceplunge.covariates.forms import SessionCovariateForm
from iceplunge.covariates.models import SessionCovariate
from iceplunge.tasks.helpers.metrics.digit_symbol import compute_digit_symbol_summary
from iceplunge.tasks.helpers.metrics.flanker import compute_flanker_summary
from iceplunge.tasks.helpers.metrics.mood import compute_mood_summary
from iceplunge.tasks.helpers.metrics.pvt import compute_pvt_summary
from iceplunge.tasks.helpers.metrics.sart import compute_sart_summary
from iceplunge.tasks.helpers.quality import compute_quality_flags
from iceplunge.tasks.helpers.rate_limits import check_voluntary_rate_limit
from iceplunge.tasks.helpers.session_helpers import (
    create_practice_session,
    create_session,
    expire_stale_session,
    increment_session_indices,
    next_task,
)
from iceplunge.tasks.models import CognitiveSession, MoodRating, TaskConfig, TaskResult, UserTaskPreference
from iceplunge.tasks.registry import TASK_REGISTRY

# Maps task_type → server-side metric compute function
_METRIC_COMPUTERS = {
    "pvt": lambda trials, duration_ms: compute_pvt_summary(trials),
    "sart": lambda trials, duration_ms: compute_sart_summary(trials),
    "mood": lambda trials, duration_ms: compute_mood_summary(trials),
    "flanker": lambda trials, duration_ms: compute_flanker_summary(trials),
    "digit_symbol": lambda trials, duration_ms: compute_digit_symbol_summary(trials, duration_ms),
}

_SESSION_KEY = "current_cognitive_session_id"


def _expiry_hours() -> int:
    from iceplunge.tasks.helpers.session_helpers import SESSION_EXPIRY_HOURS
    return SESSION_EXPIRY_HOURS


class SessionStartView(LoginRequiredMixin, View):
    """
    Creates a CognitiveSession and collects per-session covariates before
    redirecting the user to the first task.

    GET  — if an in-progress session exists, redirect straight to its hub;
           otherwise create a new session and render the covariate form.
    POST — save the covariate form, redirect to the hub.
    """

    def get(self, request):
        existing = self._find_in_progress_session(request)
        if existing:
            request.session[_SESSION_KEY] = str(existing.id)
            return redirect("tasks:hub", session_id=existing.id)
        allowed, reason = check_voluntary_rate_limit(request.user)
        if not allowed:
            return render(request, "tasks/session_start.html", {"rate_limited": True, "reason": reason}, status=429)
        session = self._create_session(request)
        form = SessionCovariateForm()
        return render(request, "tasks/session_start.html", {"form": form, "session": session})

    def post(self, request):
        existing = self._find_in_progress_session(request)
        if existing:
            request.session[_SESSION_KEY] = str(existing.id)
            return redirect("tasks:hub", session_id=existing.id)
        allowed, reason = check_voluntary_rate_limit(request.user)
        if not allowed:
            return render(request, "tasks/session_start.html", {"rate_limited": True, "reason": reason}, status=429)
        session = self._create_session(request)
        form = SessionCovariateForm(request.POST)
        if form.is_valid():
            covariate = form.save(commit=False)
            covariate.session = session
            covariate.save()
            return redirect("tasks:hub", session_id=session.id)
        return render(request, "tasks/session_start.html", {"form": form, "session": session})

    def _find_in_progress_session(self, request):
        """
        Return an existing non-practice in-progress session that has not
        expired, or None.  Stale sessions are marked ABANDONED on the way out.
        """
        from iceplunge.tasks.helpers.session_helpers import SESSION_EXPIRY_HOURS

        expiry_cutoff = timezone.now() - timedelta(hours=SESSION_EXPIRY_HOURS)

        # Expire any stale in-progress sessions for this user.
        CognitiveSession.objects.filter(
            user=request.user,
            is_practice=False,
            completion_status=CognitiveSession.CompletionStatus.IN_PROGRESS,
            started_at__lt=expiry_cutoff,
        ).update(completion_status=CognitiveSession.CompletionStatus.ABANDONED)

        # Check Django session key first (fast path)
        session_id = request.session.get(_SESSION_KEY)
        if session_id:
            try:
                return CognitiveSession.objects.get(
                    id=session_id,
                    user=request.user,
                    is_practice=False,
                    completion_status=CognitiveSession.CompletionStatus.IN_PROGRESS,
                )
            except CognitiveSession.DoesNotExist:
                pass
        # Fall back to DB query (handles cleared session cookies, other devices, etc.)
        return (
            CognitiveSession.objects.filter(
                user=request.user,
                is_practice=False,
                completion_status=CognitiveSession.CompletionStatus.IN_PROGRESS,
            )
            .order_by("-started_at")
            .first()
        )

    def _create_session(self, request):
        session = create_session(request.user)
        request.session[_SESSION_KEY] = str(session.id)
        return session


class SessionTaskView(LoginRequiredMixin, View):
    """
    Renders the task page for the next uncompleted task in the session.
    Redirects to SessionCompleteView when all tasks are done.
    """

    def get(self, request, session_id):
        session = get_object_or_404(CognitiveSession, id=session_id, user=request.user)

        if expire_stale_session(session):
            messages.warning(
                request,
                "Your session expired (sessions must be completed within "
                f"{_expiry_hours()} hour). A new session will be started when you're ready.",
            )
            request.session.pop(_SESSION_KEY, None)
            return redirect("tasks:start")

        task_type = next_task(session)
        if task_type is None:
            return redirect("tasks:hub", session_id=session.id)
        return render(
            request,
            "tasks/session_task.html",
            {
                "session": session,
                "task_type": task_type,
                "task_label": TASK_REGISTRY[task_type]["label"],
            },
        )


class SessionCompleteView(LoginRequiredMixin, View):
    """
    Marks the session as complete and renders the completion page.
    """

    def get(self, request, session_id):
        session = get_object_or_404(CognitiveSession, id=session_id, user=request.user)
        if session.completion_status == CognitiveSession.CompletionStatus.IN_PROGRESS:
            CognitiveSession.objects.filter(pk=session.pk).update(
                completion_status=CognitiveSession.CompletionStatus.COMPLETE,
                completed_at=timezone.now(),
            )
            session.refresh_from_db()
        # Clear Django session so next visit to tasks:start creates a fresh session
        request.session.pop(_SESSION_KEY, None)
        return render(request, "tasks/session_complete.html", {"session": session})


class SessionMetaView(LoginRequiredMixin, View):
    """
    Receives timezone offset and device metadata from task_core.js and stores
    them on the CognitiveSession.  Called once per page load by TaskCore.init().
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        session_id = data.get("session_id")
        if not session_id:
            return JsonResponse({"error": "session_id is required"}, status=422)

        session = get_object_or_404(CognitiveSession, id=session_id, user=request.user)

        update_fields = {}
        if "timezone_offset_minutes" in data:
            update_fields["timezone_offset_minutes"] = data["timezone_offset_minutes"]
        if "device_meta" in data:
            update_fields["device_meta"] = data["device_meta"]

        if update_fields:
            CognitiveSession.objects.filter(pk=session.pk).update(**update_fields)

        return JsonResponse({"ok": True})


class TaskResultSubmitView(LoginRequiredMixin, View):
    """
    Receives, validates, and saves a TaskResult payload from task_core.js.

    Returns:
        201 {"ok": true, "next_task": "<type|null>", "is_partial": <bool>}
        422 on validation failure
        403 session belongs to a different user
        409 session is already complete
    """

    REQUIRED_FIELDS = frozenset(
        {
            "session_id",
            "task_type",
            "task_version",
            "started_at",
            "ended_at",
            "duration_ms",
            "input_modality",
            "trials",
            "summary",
        }
    )

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=422)

        # Validate required envelope fields
        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            return JsonResponse(
                {"error": f"Missing fields: {', '.join(sorted(missing))}"},
                status=422,
            )

        # Validate task_type against registry
        task_type = data["task_type"]
        if task_type not in TASK_REGISTRY:
            return JsonResponse({"error": f"Unknown task_type: '{task_type}'"}, status=422)

        # Retrieve session and check ownership
        session_id = data["session_id"]
        try:
            session = CognitiveSession.objects.get(id=session_id)
        except (CognitiveSession.DoesNotExist, ValueError):
            return JsonResponse({"error": "Session not found"}, status=422)

        if session.user != request.user:
            return JsonResponse({"error": "Forbidden"}, status=403)

        if session.completion_status == CognitiveSession.CompletionStatus.COMPLETE:
            return JsonResponse({"error": "Session already complete"}, status=409)

        # Always persist interruptions to session regardless of save outcome
        interruptions = data.get("interruptions") or []
        if interruptions:
            session.refresh_from_db()
            meta = dict(session.device_meta or {})
            meta.setdefault("interruption_logs", []).extend(interruptions)
            CognitiveSession.objects.filter(pk=session.pk).update(device_meta=meta)

        # Partial-save logic
        is_partial = bool(data.get("is_partial", False))
        duration_ms = data["duration_ms"]
        minimum_viable_ms = TASK_REGISTRY[task_type]["minimum_viable_ms"]

        if is_partial:
            if minimum_viable_ms == 0:
                return JsonResponse(
                    {"error": "Partial save not allowed for this task type"},
                    status=422,
                )
            if duration_ms < minimum_viable_ms:
                return JsonResponse(
                    {
                        "error": (
                            f"Duration {duration_ms} ms is below the minimum viable "
                            f"threshold of {minimum_viable_ms} ms for '{task_type}'"
                        )
                    },
                    status=422,
                )

        # Parse timestamps
        started_at = parse_datetime(data["started_at"])
        completed_at = parse_datetime(data["ended_at"])
        if started_at is None or completed_at is None:
            return JsonResponse(
                {"error": "Invalid datetime format for started_at or ended_at"},
                status=422,
            )

        # Compute session indices
        overall_index, per_task_index = increment_session_indices(request.user, task_type)

        # Create TaskResult
        task_result = TaskResult.objects.create(
            session=session,
            task_type=task_type,
            task_version=data["task_version"],
            started_at=started_at,
            completed_at=completed_at,
            trial_data=data.get("trials", []),
            summary_metrics=data.get("summary", {}),
            session_index_overall=overall_index,
            session_index_per_task=per_task_index,
            is_partial=is_partial,
        )

        # Quality flags
        quality_flags = compute_quality_flags(request.user, session, task_result)
        if quality_flags:
            session.refresh_from_db()
            new_flags = list(session.quality_flags or []) + quality_flags
            CognitiveSession.objects.filter(pk=session.pk).update(quality_flags=new_flags)

        # Server-side metric re-computation + discrepancy detection
        compute_fn = _METRIC_COMPUTERS.get(task_type)
        if compute_fn:
            server_summary = compute_fn(data.get("trials", []), data["duration_ms"])
            client_summary = data.get("summary", {}) or {}

            # Detect >5% discrepancies between client and server metrics
            discrepancy_flags = []
            for key, server_val in server_summary.items():
                client_val = client_summary.get(key)
                if server_val is not None and client_val is not None:
                    try:
                        if server_val != 0 and abs((server_val - client_val) / server_val) > 0.05:
                            discrepancy_flags.append(f"metric_discrepancy_{key}")
                    except TypeError:
                        pass

            task_result.summary_metrics = server_summary
            task_result.save(update_fields=["summary_metrics"])

            if discrepancy_flags:
                session.refresh_from_db()
                new_flags = list(session.quality_flags or []) + discrepancy_flags
                CognitiveSession.objects.filter(pk=session.pk).update(quality_flags=new_flags)

            # Mood task: also create a MoodRating record
            if task_type == "mood" and all(
                server_summary.get(k) is not None
                for k in ("valence", "arousal", "stress", "sharpness")
            ):
                MoodRating.objects.get_or_create(
                    session=session,
                    defaults={
                        "valence": server_summary["valence"],
                        "arousal": server_summary["arousal"],
                        "stress": server_summary["stress"],
                        "sharpness": server_summary["sharpness"],
                    },
                )

        # Determine next task (refresh to pick up the just-created TaskResult)
        session.refresh_from_db()
        next_task_type = next_task(session)

        return JsonResponse(
            {"ok": True, "next_task": next_task_type, "is_partial": task_result.is_partial},
            status=201,
        )


class TryTaskView(View):
    """
    Opens a single-task practice run in a new tab.
    Accessible without login so visitors can try tasks from the homepage.
    Logged-in users get a real (is_practice) CognitiveSession so results are
    stored but excluded from all analyses.  Anonymous users get no DB session;
    task_core.js detects the empty session_id and skips server submission,
    showing the practice-complete dialog entirely client-side.
    """

    def get(self, request, task_type):
        import random

        if task_type not in TASK_REGISTRY:
            from django.http import Http404
            raise Http404
        if request.user.is_authenticated:
            session = create_practice_session(request.user, task_type)
            anonymous_seed = ""
        else:
            session = None
            anonymous_seed = str(random.randint(100_000, 999_999))
        return render(
            request,
            "tasks/try_task.html",
            {
                "session": session,
                "task_type": task_type,
                "task_label": TASK_REGISTRY[task_type]["label"],
                "anonymous_seed": anonymous_seed,
            },
        )


class SessionHubView(LoginRequiredMixin, View):
    """
    Between-task hub: shows all tasks in session order with completion status,
    per-task instructions, and a button to start the next task.
    """

    def get(self, request, session_id):
        session = get_object_or_404(CognitiveSession, id=session_id, user=request.user)

        if session.completion_status == CognitiveSession.CompletionStatus.COMPLETE:
            return redirect("tasks:complete", session_id=session.id)

        if expire_stale_session(session):
            messages.warning(
                request,
                "Your session expired (sessions must be completed within "
                f"{_expiry_hours()} hour). A new session will be started when you're ready.",
            )
            request.session.pop(_SESSION_KEY, None)
            return redirect("tasks:start")

        completed_types = set(session.task_results.values_list("task_type", flat=True))
        skipped_types = set((session.device_meta or {}).get("skipped_tasks", []))
        next_task_type = next_task(session)

        task_list = [
            {
                "type": t,
                "label": TASK_REGISTRY[t]["label"],
                "duration_display": TASK_REGISTRY[t]["duration_display"],
                "instructions": TASK_REGISTRY[t]["instructions"],
                "is_done": t in completed_types,
                "is_skipped": t in skipped_types,
                "is_next": t == next_task_type,
            }
            for t in session.task_order
        ]

        return render(
            request,
            "tasks/session_hub.html",
            {
                "session": session,
                "task_list": task_list,
                "next_task_type": next_task_type,
                "all_done": next_task_type is None,
            },
        )


class SessionTaskSkipView(LoginRequiredMixin, View):
    """
    Marks the current (next uncompleted) task as skipped by appending it to
    device_meta['skipped_tasks'].  Only the active next task may be skipped.

    POST body: { session_id, task_type }
    Returns:   { ok: true, next_task: <type|null> }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=422)

        session_id = data.get("session_id")
        task_type = data.get("task_type")

        if not session_id or not task_type:
            return JsonResponse({"error": "session_id and task_type are required"}, status=422)

        try:
            session = CognitiveSession.objects.get(id=session_id)
        except (CognitiveSession.DoesNotExist, ValueError):
            return JsonResponse({"error": "Session not found"}, status=422)

        if session.user != request.user:
            return JsonResponse({"error": "Forbidden"}, status=403)

        current_task = next_task(session)
        if task_type != current_task:
            return JsonResponse({"error": "Can only skip the current active task"}, status=422)

        session.refresh_from_db()
        meta = dict(session.device_meta or {})
        skipped = list(meta.get("skipped_tasks", []))
        if task_type not in skipped:
            skipped.append(task_type)
        meta["skipped_tasks"] = skipped
        CognitiveSession.objects.filter(pk=session.pk).update(device_meta=meta)

        session.refresh_from_db()
        next_task_type = next_task(session)

        return JsonResponse({"ok": True, "next_task": next_task_type})


class TaskCancelView(LoginRequiredMixin, View):
    """
    Deletes any TaskResult for the given task_type in the given session,
    ensuring no data persists if the user cancels mid-task.

    Also removes MoodRating if the cancelled task is "mood".

    POST body: { session_id, task_type }
    Returns:   { ok: true }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        session_id = data.get("session_id")
        task_type = data.get("task_type")

        if not session_id or not task_type:
            return JsonResponse({"error": "session_id and task_type are required"}, status=422)

        try:
            session = CognitiveSession.objects.get(id=session_id, user=request.user)
        except (CognitiveSession.DoesNotExist, ValueError):
            return JsonResponse({"error": "Session not found"}, status=422)

        TaskResult.objects.filter(session=session, task_type=task_type).delete()

        if task_type == "mood":
            MoodRating.objects.filter(session=session).delete()

        return JsonResponse({"ok": True})


class SessionTaskUnskipView(LoginRequiredMixin, View):
    """
    Removes a previously skipped task from device_meta['skipped_tasks'],
    allowing the user to attempt it.  Any skipped task in the session may
    be un-skipped; ordering is determined by task_order as usual.

    POST body: { session_id, task_type }
    Returns:   { ok: true }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=422)

        session_id = data.get("session_id")
        task_type = data.get("task_type")

        if not session_id or not task_type:
            return JsonResponse({"error": "session_id and task_type are required"}, status=422)

        try:
            session = CognitiveSession.objects.get(id=session_id)
        except (CognitiveSession.DoesNotExist, ValueError):
            return JsonResponse({"error": "Session not found"}, status=422)

        if session.user != request.user:
            return JsonResponse({"error": "Forbidden"}, status=403)

        meta = dict(session.device_meta or {})
        skipped = [t for t in meta.get("skipped_tasks", []) if t != task_type]
        meta["skipped_tasks"] = skipped
        CognitiveSession.objects.filter(pk=session.pk).update(device_meta=meta)

        return JsonResponse({"ok": True})


class TaskPreferenceView(LoginRequiredMixin, View):
    """
    Lets users choose which tasks appear in their sessions.
    GET  — show all globally-enabled tasks with the user's current opt-outs.
    POST — save updated opt-outs from checkbox form.
    """

    template_name = "tasks/task_preferences.html"

    def _task_list(self, user):
        """Return task metadata annotated with whether the user has enabled each one."""
        globally_enabled = set(
            TaskConfig.objects.filter(is_enabled=True).values_list("task_type", flat=True)
        )
        try:
            pref = UserTaskPreference.objects.get(user=user)
            user_disabled = set(pref.disabled_task_types)
        except UserTaskPreference.DoesNotExist:
            user_disabled = set()

        return [
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

    def get(self, request):
        return render(request, self.template_name, {"task_list": self._task_list(request.user)})

    def post(self, request):
        globally_enabled = set(
            TaskConfig.objects.filter(is_enabled=True).values_list("task_type", flat=True)
        )
        selected = set(request.POST.getlist("task_types"))
        disabled = [t for t in globally_enabled if t not in selected]

        pref, _ = UserTaskPreference.objects.get_or_create(user=request.user)
        pref.disabled_task_types = disabled
        pref.save(update_fields=["disabled_task_types"])

        messages.success(request, "Your task preferences have been saved.")
        return redirect("settings")


session_start_view = SessionStartView.as_view()
try_task_view = TryTaskView.as_view()
session_hub_view = SessionHubView.as_view()
session_task_view = SessionTaskView.as_view()
session_complete_view = SessionCompleteView.as_view()
session_meta_view = SessionMetaView.as_view()
task_result_submit_view = TaskResultSubmitView.as_view()
task_cancel_view = TaskCancelView.as_view()
session_task_skip_view = SessionTaskSkipView.as_view()
session_task_unskip_view = SessionTaskUnskipView.as_view()
task_preference_view = TaskPreferenceView.as_view()

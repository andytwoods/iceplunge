# Ice Plunge Platform – Phased Build Tasks

> Each task is sized to be completable in one focused LLM session.
> Always read `OVERVIEW.md` and `.junie/guidelines.md` before starting any task.
> Tasks within a phase may be done in any order unless a `Depends on` field says otherwise.

## Project structure reference

> Read this before touching any file path in the tasks below.

- `APPS_DIR` = `iceplunge/` — all project apps live here.
- Module paths in settings: `"iceplunge.<appname>"` (e.g. `"iceplunge.plunges"`).
- App code: `iceplunge/<appname>/models.py`, `views.py`, etc.
- Templates: `iceplunge/templates/<appname>/` — the global template dir; **not** per-app dirs.
- HTMX partials: `iceplunge/templates/<appname>/partials/_<name>.html`.
- Static files: `iceplunge/static/<appname>/`.
- Dependencies: managed with `uv` via `pyproject.toml`. Use `uv add <pkg>` / `uv remove <pkg>`.
- User model: `iceplunge/users/models.py`, always accessed via `get_user_model()`. Email-only login; has `name` field; no `first_name`/`last_name`.

---

## Testing policy

Every acceptance criterion must be covered by an automated test **unless it is marked `(manual)`**.

- **Automated** means a Django `TestCase` or `pytest` test that runs in CI with no browser.
- **`(manual)`** means the criterion requires a human to verify in a browser (JS behaviour, visual rendering, browser events). Do not skip these — note them in a `MANUAL_CHECKS.md` file in the relevant app so they can be verified before each release.
- **Shell checks** (`manage.py check`, `npx cap sync`, etc.) are not unit tests; they must pass in CI as part of the build step.
- `guidelines.md` mandates success *and* failure path coverage. Acceptance criteria define the minimum; add further tests wherever behaviour is non-trivial.

---

## Phase 0 — Foundation ✅

### T0.1 Complete the scaffold setup ✅
**Goal:** The cookiecutter-django scaffold is already in place. This task finishes the project-specific setup on top of it.

**Spec refs:** §2 Architecture, §13 Data Models, `.junie/guidelines.md` Project Scaffold

**What the scaffold already provides (do not recreate):**
- `config/settings/base.py|local.py|production.py|test.py`, `manage.py`, `pyproject.toml` with `uv`.
- `iceplunge/users/` app with custom `User` model (`AUTH_USER_MODEL = "users.User"`), email-only login, allauth wired, email verification mandatory.
- `iceplunge/templates/base.html` (currently Bootstrap-based — to be replaced below).
- Whitenoise, Redis, django-environ, argon2 passwords, Ruff, pytest.

**Deliverables:**
- Create and register these apps in `LOCAL_APPS` in `config/settings/base.py` (apps live under `iceplunge/`):
  `iceplunge.pages`, `iceplunge.plunges`, `iceplunge.tasks`, `iceplunge.covariates`, `iceplunge.notifications`, `iceplunge.dashboard`, `iceplunge.export`.
- Add dependencies via `uv add`: `django-hijack`, `crispy-bulma`, `django-htmx`, `huey`, `django-rollbar`. Remove `crispy-bootstrap5` via `uv remove`.
- Replace Bootstrap with **Bulma** in `iceplunge/templates/base.html`: remove Bootstrap CDN links/scripts; self-host Bulma CSS in `iceplunge/static/css/`; self-host HTMX and SweetAlert2 in `iceplunge/static/js/`.
- Update `config/settings/base.py`: `CRISPY_TEMPLATE_PACK = "bulma"`, `CRISPY_ALLOWED_TEMPLATE_PACKS = "bulma"`.
- `iceplunge/templates/base.html` must include `{% block content %}` and the hijack warning banner (hidden unless `{% if request.user.is_impersonated %}`).

**Acceptance criteria:**
- `python manage.py check` passes with no errors.
- `python manage.py runserver` serves a 200 response at `/`. *(manual)*
- All seven new apps appear in `INSTALLED_APPS`.
- No Bootstrap CSS or JS references remain in `base.html`. *(manual)*

---

### T0.2 Authentication setup ✅
**Goal:** Wire up django-allauth with email/password + Google + GitHub, plus django-hijack for admin impersonation.

**Spec refs:** §12 Onboarding, `.junie/guidelines.md` Authentication & User Impersonation sections

**Deliverables:**
- `allauth` configured in `settings/base.py`: `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`, Google and GitHub social providers added.
- `django-hijack` installed; hijack button visible in Django admin user list/detail; only superusers and `is_staff` with explicit `hijack` permission can hijack.
- Hijack session banner renders in `base.html` when a session is hijacked.
- URL patterns for allauth and hijack wired in `config/urls.py`.
- The cookiecutter `users` app already contains the custom `User` model. Add a `pseudonymised_id` field (`UUIDField`, default=`uuid4`, unique) to `iceplunge/users/models.py` — do **not** create a new `accounts` app. Always reference the User model via `get_user_model()`.

**Acceptance criteria:**
- `python manage.py migrate` completes without error.
- Admin shows hijack button; non-staff users cannot hijack. *(manual: visual button check in admin UI)*
- Attempting to access a protected view while unauthenticated redirects to login.

---

### T0.3 Consent gate middleware ✅
**Goal:** Any authenticated user who has not completed the consent flow is redirected to the consent page before accessing any other view.

**Spec refs:** §19 Ethics, §12 Onboarding

**Deliverables:**
- `ConsentProfile` model in `iceplunge/users/models.py` with fields: `user` (OneToOne), `consented_at` (DateTimeField, nullable), `consent_version` (CharField).
- Django middleware class `iceplunge/users/middleware.py::ConsentRequiredMiddleware` that redirects to `users:consent` if the user is authenticated but `ConsentProfile.consented_at` is null.
- Exempts: allauth URLs, hijack URLs, the consent view itself, static/media.
- Consent view (`iceplunge/users/views.py`): GET renders consent text; POST records `consented_at = now()` and redirects to dashboard.
- Template at `iceplunge/templates/users/consent.html`.

**Acceptance criteria:**
- New user after email verification is redirected to consent before reaching any other page.
- After consenting, subsequent requests pass through freely.
- Unit test: unauthenticated user is not redirected by the middleware.

---

## Phase 1 — Data Models ✅

### T1.1 Baseline profile model ✅
**Goal:** Capture once-per-user demographic and background covariates.

**Spec refs:** §6 Covariates (Baseline), §12 Onboarding, §13 Data Models

**Deliverables:**
- `BaselineProfile` model in `iceplunge/users/models.py`:
  - `user` (OneToOne → `User`, related_name `baseline_profile`)
  - `age` (PositiveSmallIntegerField)
  - `gender` (CharField, max_length=50)
  - `height_cm` (DecimalField, max_digits=5, decimal_places=1)
  - `weight_kg` (DecimalField, max_digits=5, decimal_places=1)
  - `bmi` (DecimalField, max_digits=5, decimal_places=2, editable=False) — computed on save
  - `handedness` (CharField, choices: left/right/ambidextrous)
  - `plunge_years` (DecimalField, max_digits=4, decimal_places=1)
  - `__str__` returns `f"Baseline: {self.user}"`
- ModelForm `BaselineProfileForm` with crispy-bulma layout.
- View + template for initial completion (shown after consent) and editing in profile settings.
- Migration.

**Acceptance criteria:**
- `bmi` is auto-computed from `weight_kg` / (`height_cm` / 100) ** 2 on every save.
- Form renders with Bulma classes via crispy-bulma. *(manual)*
- Unit test: saving the form creates a `BaselineProfile` with correct BMI.

---

### T1.2 Plunge log model ✅
**Goal:** Record every cold plunge a participant performs.

**Spec refs:** §5 Plunge Logging, §13 Data Models

**Deliverables:**
- `PlungeLog` model in `iceplunge/plunges/models.py`:
  - `user` (FK → `User`, related_name `plunge_logs`)
  - `timestamp` (DateTimeField, default=now)
  - `duration_minutes` (PositiveSmallIntegerField)
  - `water_temp_celsius` (DecimalField, max_digits=4, decimal_places=1, null=True, blank=True)
  - `temp_measured` (BooleanField, default=False)
  - `immersion_depth` (CharField, choices: waist/chest/neck)
  - `context` (CharField, choices: bath/lake/sea/cryotherapy/other)
  - `breathing_technique` (CharField, max_length=100, blank=True)
  - `perceived_intensity` (PositiveSmallIntegerField, choices 1–5)
  - `thermal_sensation` (PositiveSmallIntegerField, choices 1–5, null=True, blank=True) — how cold the participant felt (1 = not cold at all, 5 = extremely cold); captured immediately post-plunge
  - `__str__` returns `f"{self.user} – {self.timestamp:%Y-%m-%d %H:%M}"`
- Index on `(user, timestamp)`.
- Migration.

**Acceptance criteria:**
- `python manage.py migrate` succeeds.
- Admin registers `PlungeLog` with list display showing user, timestamp, context. *(manual)*

---

### T1.3 Prompt and session models ✅
**Goal:** Track every notification sent and every cognitive assessment session.

**Spec refs:** §11 Notification Schedule, §13 Data Models, §16 Compliance

**Deliverables:**
- `PromptEvent` model in `iceplunge/notifications/models.py`:
  - `user` (FK → `User`, related_name `prompt_events`)
  - `scheduled_at` (DateTimeField)
  - `sent_at` (DateTimeField, null=True, blank=True)
  - `opened_at` (DateTimeField, null=True, blank=True)
  - `prompt_type` (CharField, choices: reactive/scheduled)
  - `linked_plunge` (FK → `PlungeLog`, null=True, blank=True, on_delete=SET_NULL)
  - `__str__` returns `f"{self.user} – {self.prompt_type} – {self.scheduled_at:%Y-%m-%d %H:%M}"`
- `CognitiveSession` model in `iceplunge/tasks/models.py`:
  - `id` (UUIDField, primary_key, default=uuid4)
  - `user` (FK → `User`, related_name `cognitive_sessions`)
  - `prompt_event` (FK → `PromptEvent`, null=True, blank=True, on_delete=SET_NULL)
  - `started_at` (DateTimeField, null=True, blank=True)
  - `completed_at` (DateTimeField, null=True, blank=True)
  - `task_order` (JSONField) — list of task_type strings in presentation order
  - `random_seed` (CharField, max_length=64)
  - `device_meta` (JSONField, default=dict)
  - `timezone_offset_minutes` (SmallIntegerField, null=True, blank=True) — client's UTC offset in minutes at session start (e.g. +60 for BST), captured by `task_core.js` via `new Date().getTimezoneOffset()` and sent with session initialisation; used to derive local time-of-day for analysis
  - `completion_status` (CharField, choices: complete/abandoned/in_progress, default=in_progress)
  - `quality_flags` (JSONField, default=list)
  - `is_practice` (BooleanField, default=False)
  - `__str__` returns `f"Session {self.id} – {self.user}"`
- Indexes on `(user, started_at)`, `(user, completion_status)`.
- Migrations.

**Acceptance criteria:**
- Both models registered in admin.
- Unit test: creating a `CognitiveSession` with a UUID primary key persists and retrieves correctly.

---

### T1.4 Task result and mood models ✅
**Goal:** Store trial-level and session-level cognitive task data.

**Spec refs:** §3 Modularity (payload schema), §4 Battery, §13 Data Models

**Deliverables:**
- `TaskResult` model in `iceplunge/tasks/models.py`:
  - `id` (UUIDField, primary_key, default=uuid4)
  - `session` (FK → `CognitiveSession`, related_name `task_results`, on_delete=CASCADE)
  - `task_type` (CharField, max_length=50) — validated against `TASK_REGISTRY` on save
  - `task_version` (CharField, max_length=20)
  - `started_at` (DateTimeField)
  - `completed_at` (DateTimeField)
  - `trial_data` (JSONField) — array of trial objects
  - `summary_metrics` (JSONField) — task-specific derived metrics
  - `session_index_overall` (PositiveIntegerField) — how many times this user has done any task
  - `session_index_per_task` (PositiveIntegerField) — how many times this user has done this task type
  - `is_acclimatisation` (BooleanField, default=False)
  - `is_partial` (BooleanField, default=False) — True when the task was interrupted after the minimum viable threshold but saved anyway (see T4.3)
  - `__str__` returns `f"{self.task_type} v{self.task_version} – {self.session}"`
- `MoodRating` model in `iceplunge/tasks/models.py`:
  - `session` (OneToOne → `CognitiveSession`, related_name `mood_rating`)
  - `valence` (PositiveSmallIntegerField, choices 1–5)
  - `arousal` (PositiveSmallIntegerField, choices 1–5)
  - `stress` (PositiveSmallIntegerField, choices 1–5)
  - `sharpness` (PositiveSmallIntegerField, choices 1–5)
  - `__str__` returns `f"Mood – {self.session}"`
- `TASK_REGISTRY` dict defined in `iceplunge/tasks/registry.py` with all five task types; each entry gains a `minimum_viable_ms` key (e.g. PVT: 30 000, SART: 30 000, flanker: 30 000, digit_symbol: 30 000, mood: 0 — mood has no meaningful partial).
- `TaskResult.clean()` raises `ValidationError` if `task_type` not in `TASK_REGISTRY`.
- Migrations.

**Acceptance criteria:**
- Saving a `TaskResult` with an invalid `task_type` raises `ValidationError`.
- Unit test: `session_index_per_task` is set correctly when multiple `TaskResult` records exist for the same user/task.

---

### T1.5 Covariate models ✅
**Goal:** Store daily and weekly self-report covariates.

**Spec refs:** §6 Covariates (Daily, Weekly), §13 Data Models

**Deliverables:**
- `DailyCovariate` model in `iceplunge/covariates/models.py`:
  - `user` (FK → `User`, related_name `daily_covariates`)
  - `date` (DateField)
  - `sleep_duration_hours` (DecimalField, max_digits=4, decimal_places=1, null=True, blank=True)
  - `sleep_quality` (PositiveSmallIntegerField, choices 1–5, null=True, blank=True)
  - `alcohol_last_24h` (BooleanField, null=True, blank=True)
  - `exercise_today` (BooleanField, null=True, blank=True)
  - `unique_together`: `(user, date)`
  - `__str__` returns `f"Daily: {self.user} – {self.date}"`
- `WeeklyCovariate` model in `iceplunge/covariates/models.py`:
  - `user` (FK → `User`, related_name `weekly_covariates`)
  - `week_start` (DateField) — Monday of the week
  - `gi_severity` (PositiveSmallIntegerField, choices 1–5, null=True, blank=True)
  - `gi_symptoms` (JSONField, default=list) — list of symptom strings from a checkbox set
  - `illness_status` (BooleanField, null=True, blank=True)
  - `unique_together`: `(user, week_start)`
  - `__str__` returns `f"Weekly: {self.user} – {self.week_start}"`
- Migrations.

**Acceptance criteria:**
- `unique_together` constraints enforced at the DB level.
- Admin registers both models.

---

## Phase 2 — Plunge Logging ✅

### T2.1 Plunge log CRUD views ✅
**Goal:** Participants can log, view, and delete their plunges via an HTMX-powered interface.

**Spec refs:** §5 Plunge Logging, `.junie/guidelines.md` HTMX, Views

**Deliverables:**
- `iceplunge/plunges/views.py`:
  - `PlungeListView` (login required) — lists user's own plunges, paginated (20/page).
  - `PlungeCreateView` — ModelForm; HTMX request returns `_plunge_row.html` partial prepended to list; full request returns the list page.
  - `PlungeDeleteView` — requires `user == request.user`; on HTMX request returns empty 200 to trigger row removal.
- Templates:
  - `iceplunge/templates/plunges/plunge_list.html`
  - `iceplunge/templates/plunges/partials/_plunge_form.html`
  - `iceplunge/templates/plunges/partials/_plunge_row.html`
- URL names: `plunges:list`, `plunges:create`, `plunges:delete`.

**Acceptance criteria:**
- Submitting the create form via HTMX inserts a new row without full page reload. *(manual)*
- A user cannot delete another user's plunge (returns 404).
- Unit tests cover create success, delete by owner, delete attempt by other user.

---

### T2.2 Derived variable computation ✅
**Goal:** Compute and store plunge-relative derived variables on each `CognitiveSession` at creation time.

**Spec refs:** §7 Derived Variables, §13 Derived Variables

**Deliverables:**
- `iceplunge/plunges/helpers/derived.py` with pure functions (no Django ORM calls):
  - `time_since_last_plunge(plunge_logs, session_dt)` → `timedelta | None`
  - `proximity_bin(delta)` → one of: `"pre"`, `"0-15m"`, `"15-60m"`, `"1-3h"`, `">3h"`, `"no_plunge"`
  - `same_day_plunge_count(plunge_logs, session_date)` → `int`
  - `rolling_frequency(plunge_logs, session_dt, days)` → `float` (plunges per day over window)
  - `season(dt)` → one of: `"spring"`, `"summer"`, `"autumn"`, `"winter"` (northern hemisphere)
- `iceplunge/plunges/helpers/session_derived.py`:
  - `compute_session_derived(user, session_dt)` → dict with all derived variable values; queries DB internally.
- `CognitiveSession.derived_variables` (JSONField, default=dict) — add field + migration.
- `tasks/signals.py` — `post_save` on `CognitiveSession` (status transitions to `in_progress`) calls `compute_session_derived` and stores result.

**Acceptance criteria:**
- Unit tests for each function in `derived.py` covering boundary cases (no plunges, plunge 5 min ago, plunge yesterday).
- `proximity_bin` returns `"0-15m"` for a 10-minute delta.

---

## Phase 3 — Covariates Collection ✅

### T3.1 Daily and weekly covariate forms ✅
**Goal:** Participants are prompted for daily covariates once per day and weekly covariates once per week, embedded in the session flow.

**Spec refs:** §6 Covariates, §12 Onboarding

**Deliverables:**
- `iceplunge/covariates/forms.py`: `DailyCovariateForm`, `WeeklyCovariateForm` (ModelForms, crispy-bulma).
- `iceplunge/covariates/views.py`:
  - `DailyCovariateView` — creates or updates today's record for the user; HTMX-aware (returns partial on HTMX, redirect on full).
  - `WeeklyCovariateView` — same pattern for the current week.
- Templates:
  - `iceplunge/templates/covariates/partials/_daily_form.html`
  - `iceplunge/templates/covariates/partials/_weekly_form.html`
- Helper `iceplunge/covariates/helpers.py::needs_daily_covariate(user)` → bool (true if no record for today).
- Helper `iceplunge/covariates/helpers.py::needs_weekly_covariate(user)` → bool (true if no record for current week).
- URL names: `covariates:daily`, `covariates:weekly`.

**Acceptance criteria:**
- Submitting daily form twice on the same day updates the existing record, not creates a duplicate.
- Unit tests for both helper functions.

---

### T3.2 Per-session covariate collection ✅
**Goal:** Capture caffeine, last-meal, and hand-state data at the start of each cognitive session.

**Spec refs:** §6 Covariates (Per Session), §13 Data Models

**Deliverables:**
- `SessionCovariate` model in `iceplunge/covariates/models.py`:
  - `session` (OneToOne → `CognitiveSession`, related_name `session_covariate`)
  - `caffeine_since_last_session` (BooleanField, null=True, blank=True)
  - `minutes_since_last_meal` (PositiveSmallIntegerField, null=True, blank=True)
  - `cold_hands` (BooleanField, null=True, blank=True) — hands feeling cold at session start; confound for touch RT
  - `wet_hands` (BooleanField, null=True, blank=True) — hands wet at session start (e.g. immediately post-plunge); confound for touch RT
  - `__str__` returns `f"SessionCovariate – {self.session}"`
- `SessionCovariateForm` in `iceplunge/covariates/forms.py`.
- Migration.
- The session start view (Phase 5) will render this form before the first task loads.

**Acceptance criteria:**
- Migration applies cleanly.
- Admin registers the model.

---

## Phase 4 — Task Infrastructure ✅

### T4.1 Task registry and session orchestration (backend) ✅
**Goal:** Backend logic to create a `CognitiveSession`, select and order tasks, and serve them one at a time.

**Spec refs:** §3 Modularity (Backend Task Registry, Randomisation), §13 Models

**Deliverables:**
- `iceplunge/tasks/registry.py` containing `TASK_REGISTRY` dict (five entries from §3).
- `iceplunge/tasks/helpers/session_helpers.py`:
  - `create_session(user, prompt_event=None, is_practice=False)` → `CognitiveSession`; randomises task order per §3 Randomisation; stores seed and task order on the session; computes derived variables via Phase 2.
  - `next_task(session)` → task_type string of the next uncompleted task, or `None` if all done.
  - `increment_session_indices(user, task_type)` → `(overall_index, per_task_index)`.
- `iceplunge/tasks/views.py`:
  - `SessionStartView` — creates session (calls `create_session`), renders session-covariate form if not already submitted today, then redirects to first task.
  - `SessionTaskView` — loads the correct task partial via HTMX; determines which task is next using `next_task(session)`.
  - `SessionCompleteView` — marks session as complete; redirects to dashboard.
- URL names: `tasks:start`, `tasks:task`, `tasks:complete`.

**Acceptance criteria:**
- Unit test: `create_session` produces a session with all five core tasks in a randomised order; the same seed always produces the same order.
- Unit test: `next_task` returns `None` after all tasks are submitted.
- Rotating task included at most once per day.

---

### T4.2 `task_core.js` shared library ✅
**Goal:** Shared JS library that all task modules call for timing, submission, and event handling.

**Spec refs:** §3 Modularity (JS Interface Contract, Lifecycle Event Handling, Payload Schema)

**Deliverables:**
- `iceplunge/static/tasks/js/task_core.js` — plain JS module (no bundler required), exported as `window.TaskCore`.
- Public API:
  - `TaskCore.init(sessionId, csrfToken)` — called once per page load; captures `new Date().getTimezoneOffset()` and POSTs it to `tasks:session_meta` alongside OS/device info so the server can store it on `CognitiveSession.timezone_offset_minutes`.
  - `TaskCore.submit(payload)` — validates the mandatory envelope fields, POSTs to `tasks:submit_result` via `fetch`, returns a Promise; rejects if any mandatory field is missing; on 422 response throws a descriptive error.
  - `TaskCore.logEvent(type, detail)` — appends to an in-memory interruption log; included automatically in every `submit` payload as `interruptions`.
  - `TaskCore.now()` → `performance.now()` offset in ms from `TaskCore.init`.
  - `TaskCore.wallClock()` → ISO-8601 UTC string using `Date`.
  - Automatically attaches `visibilitychange`, `pagehide`, `beforeunload` listeners; calls the active task's `pause()` / `abort()` as per the lifecycle table in §3.
  - `TaskCore.registerTask(taskObject)` — registers the `{ init, pause, resume, abort }` interface for the current task; replaces any previous registration.
  - **Offline detection:** listens for the `offline` browser event; on `offline`, calls `abort("offline")` on the active task and displays a non-blocking user message ("You appear to be offline — your progress up to this point has been noted. Reconnect to continue."); listens for `online` event and prompts the user to restart the session. Submission via `submit()` also checks `navigator.onLine` before attempting `fetch` and rejects immediately with a descriptive error if offline.

**Acceptance criteria:**
- `TaskCore.submit` with a missing `session_id` throws before making a network request.
- Manual test: backgrounding the browser tab during a task logs an interruption event.

---

### T4.3 Task result submission endpoint ✅
**Goal:** Backend endpoint that receives, validates, and saves a `TaskResult` payload.

**Spec refs:** §3 (Payload Schema), §18 Data Integrity

**Deliverables:**
- `iceplunge/tasks/views.py::TaskResultSubmitView` (POST only, login required):
  - Validates envelope fields (session_id, task_type, task_version, started_at, ended_at, duration_ms, input_modality, trials, summary); returns 422 with error detail if invalid.
  - Rejects if `task_type` not in `TASK_REGISTRY`; returns 422.
  - Rejects if session does not belong to the requesting user; returns 403.
  - Rejects if session `completion_status` is already `complete`; returns 409.
  - **Partial-save logic:** if the payload includes `"is_partial": true`, the server checks `duration_ms` against `TASK_REGISTRY[task_type]["minimum_viable_ms"]`. If `duration_ms >= minimum_viable_ms`, the result is saved with `TaskResult.is_partial = True` and the `CognitiveSession.completion_status` remains `abandoned`. If below the minimum, the payload is rejected with 422 and the data discarded. Mood (`minimum_viable_ms = 0`) never saves partial. This replaces the previous hard "no partial save" rule — the `CognitiveSession` and interruption log are **always** persisted regardless.
  - Creates `TaskResult`; sets `session_index_overall` and `session_index_per_task` via `increment_session_indices`.
  - Server re-derives summary metrics and stores discrepancy flag in `quality_flags` if they differ from client values by more than 5%.
  - Returns 201 JSON `{ "ok": true, "next_task": "<type or null>", "is_partial": <bool> }`.
- URL name: `tasks:submit_result`.

**Acceptance criteria:**
- Unit tests: 422 on missing field, 403 on wrong user, 409 on already-complete session, 201 on valid payload.
- Unit test: partial payload with `duration_ms >= minimum_viable_ms` saves with `is_partial=True`; partial payload below threshold returns 422.
- Unit test: `CognitiveSession` and interruption log are saved even when the task result is discarded.
- Valid submission creates a `TaskResult` with correct `session_index_per_task`.

---

## Phase 5 — Cognitive Tasks ✅

> All tasks in this phase depend on T4.1 and T4.2.
> Each task delivers: one JS file, one partial template, server-side summary metric computation, and unit tests for the metric functions.

---

### T5.1 PVT task ✅
**Goal:** Implement the 1-minute Psychomotor Vigilance Task.

**Spec refs:** §4 Core Battery (PVT), §3 (all contracts)

**Deliverables:**
- `iceplunge/static/tasks/js/pvt.js` — implements the JS interface contract:
  - Displays a black screen with a red countdown timer that appears at random inter-stimulus intervals (2–10 s, seeded from `config.seed`).
  - Participant taps/clicks to respond; RT recorded in ms via `TaskCore.now()`.
  - Tracks anticipations (RT < 100 ms) and non-responses (>2000 ms treated as lapse).
  - Runs for `config.durationMs` (default 60 000 ms) then auto-submits.
- `iceplunge/templates/tasks/partials/_pvt.html` — root div, minimal UI, loads `pvt.js`.
- `iceplunge/tasks/helpers/metrics/pvt.py`:
  - `compute_pvt_summary(trials)` → dict with: `median_rt`, `mean_rt`, `rt_sd`, `lapse_count` (RT > 500 ms), `anticipation_count` (RT < 100 ms), `valid_trial_count`.
- Summary computed server-side in `TaskResultSubmitView` and stored in `TaskResult.summary_metrics`.

**Acceptance criteria:**
- Unit tests for `compute_pvt_summary` with known trial data.
- JS: after 60 s the task calls `TaskCore.submit` without manual interaction. *(manual)*
- A paused task does not record the pause duration as response time. *(manual)*

---

### T5.2 SART task ✅
**Goal:** Implement the SART-style sustained attention / inhibition task.

**Spec refs:** §4 Core Battery (SART)

**Deliverables:**
- `iceplunge/static/tasks/js/sart.js`:
  - Displays digits 1–9 in rapid succession (approx. 250 ms stimulus, 900 ms ISI).
  - No-go target: digit 3 (appears ~11% of trials, seeded random).
  - Participant taps for every digit except 3.
  - Correct go: response detected within response window.  Commission error: response on digit 3.  Omission: no response to go digit.
  - Runs for `config.durationMs` (60–90 s, default 75 000 ms).
- `iceplunge/templates/tasks/partials/_sart.html`.
- `iceplunge/tasks/helpers/metrics/sart.py`:
  - `compute_sart_summary(trials)` → dict with: `commission_errors`, `omission_errors`, `go_median_rt`, `go_rt_sd`, `post_error_slowing` (mean RT on trial after error vs overall, null if < 3 errors).

**Acceptance criteria:**
- Unit tests for `compute_sart_summary` including edge case of zero commission errors.
- No-go digit appears with correct approximate frequency across a simulated 100-trial run. *(manual)*

---

### T5.3 Mood rating task ✅
**Goal:** Implement the 4-item mood/subjective state rating.

**Spec refs:** §4 Core Battery (Mood), §13 MoodRating model

**Deliverables:**
- `iceplunge/static/tasks/js/mood.js`:
  - Renders four 5-point scales (valence, arousal, stress, sharpness) as horizontal icon-anchored sliders.
  - Submit button enabled only after all four are rated.
  - Completes in < 15 s; records `started_at` and `ended_at`.
- `iceplunge/templates/tasks/partials/_mood.html`.
- On submission, in addition to creating a `TaskResult`, the submit view creates a `MoodRating` record using the summary values.
- `iceplunge/tasks/helpers/metrics/mood.py`:
  - `compute_mood_summary(trials)` → dict with keys `valence`, `arousal`, `stress`, `sharpness` (integers 1–5).

**Acceptance criteria:**
- Submit button is disabled until all four scales have a value. *(manual)*
- `MoodRating` record is created alongside `TaskResult` on valid submission.
- Unit test: `compute_mood_summary` returns correct values from a trial payload.

---

### T5.4 Flanker task ✅
**Goal:** Implement the Eriksen Flanker selective-attention task (rotating module).

**Spec refs:** §4 Rotating Modules (Flanker)

**Deliverables:**
- `iceplunge/static/tasks/js/flanker.js`:
  - Displays rows of five arrows (e.g., `< < < < <` or `< < > < <`).
  - Congruent (all same direction) and incongruent (centre differs) trials in ~50/50 ratio, seeded.
  - Participant responds with left/right key or on-screen button.
  - 500 ms response window; 500 ms blank ISI.
  - Runs for `config.durationMs` (default 75 000 ms).
- `iceplunge/templates/tasks/partials/_flanker.html`.
- `iceplunge/tasks/helpers/metrics/flanker.py`:
  - `compute_flanker_summary(trials)` → dict with: `congruent_median_rt`, `incongruent_median_rt`, `conflict_effect_ms`, `congruent_accuracy`, `incongruent_accuracy`.

**Acceptance criteria:**
- Unit tests for `compute_flanker_summary` with a mixed trial set.
- `conflict_effect_ms` equals `incongruent_median_rt - congruent_median_rt`.

---

### T5.5 Digit Symbol task ✅
**Goal:** Implement the processing speed digit-symbol substitution task (rotating module).

**Spec refs:** §4 Rotating Modules (Digit Symbol)

**Deliverables:**
- `iceplunge/static/tasks/js/digit_symbol.js`:
  - Displays a fixed key (digits 1–9 mapped to unique symbols) at the top.
  - One digit shown at a time; participant selects the matching symbol from 4 options.
  - Seeded randomisation of digit order and distractor symbols.
  - Runs for `config.durationMs` (default 75 000 ms).
- `iceplunge/templates/tasks/partials/_digit_symbol.html`.
- `iceplunge/tasks/helpers/metrics/digit_symbol.py`:
  - `compute_digit_symbol_summary(trials)` → dict with: `correct_per_minute`, `total_correct`, `total_errors`, `error_rate`.

**Acceptance criteria:**
- Unit test: `correct_per_minute` is computed from `total_correct / (duration_ms / 60000)`.
- Symbols are randomised per-session (not hardcoded) but deterministic given the seed.

---

## Phase 6 — Notifications ✅

### T6.1 OneSignal integration ✅
**Goal:** Connect the Django backend to OneSignal so push notifications can be sent programmatically.

**Spec refs:** §10 Reliability, §11 Notification Schedule

**Deliverables:**
- `ONESIGNAL_APP_ID` and `ONESIGNAL_API_KEY` read from env vars in `settings/base.py`.
- `iceplunge/notifications/onesignal.py`:
  - `send_push(user, title, body, data=None)` → sends a notification to the user's OneSignal external user ID; returns response dict.
  - `register_device(user, onesignal_player_id)` — stores player ID on user's `NotificationProfile`.
- `NotificationProfile` model in `iceplunge/notifications/models.py`:
  - `user` (OneToOne), `onesignal_player_id` (CharField, blank=True), `push_enabled` (BooleanField, default=True), `morning_window_start` (TimeField, default=08:00), `evening_window_start` (TimeField, default=18:00).
- `iceplunge/notifications/views.py::RegisterDeviceView` — receives player ID from Capacitor JS and saves it.
- Migration.

**Acceptance criteria:**
- `send_push` raises a specific exception (not a catch-all) if OneSignal returns a non-2xx response.
- Unit test for `register_device` using a mock.

---

### T6.2 Reactive prompt scheduling ✅
**Goal:** After a plunge is logged, automatically schedule two post-plunge cognitive prompts.

**Spec refs:** §11 Notification Schedule (Reactive prompts), §16 Compliance

**Deliverables:**
- `iceplunge/notifications/helpers/scheduling.py`:
  - `schedule_reactive_prompts(plunge_log)` — creates two `PromptEvent` records (15–30 min post-plunge, 2–3 h post-plunge) and enqueues Huey tasks to send them; respects daily cap and 45-minute gap rule.
  - `daily_prompt_count(user, date)` → int.
  - `minutes_since_last_prompt(user)` → int | None.
- `iceplunge/notifications/tasks.py`:
  - `send_prompt_task(prompt_event_id)` — Huey-decorated; calls `send_push`; records `sent_at` on `PromptEvent`.
- `iceplunge/plunges/signals.py` — `post_save` on `PlungeLog` (created=True) calls `schedule_reactive_prompts`.

**Acceptance criteria:**
- Unit test: calling `schedule_reactive_prompts` when the user is already at the daily cap creates no new `PromptEvent` records.
- Unit test: two `PromptEvent` records are created with correct `scheduled_at` values when cap allows.

---

### T6.3 Scheduled daily prompts ✅
**Goal:** Send morning and evening prompts each day for all opted-in participants.

**Spec refs:** §11 Notification Schedule (Scheduled prompts)

**Deliverables:**
- `iceplunge/notifications/helpers/scheduling.py`:
  - `schedule_daily_prompts_for_user(user, date)` — creates morning and evening `PromptEvent` records if the user hasn't hit the daily cap; enqueues Huey tasks at the correct local times.
  - `should_send_scheduled_prompt(user, prompt_type)` → bool (checks cap, gap, push_enabled).
- `iceplunge/notifications/tasks.py`:
  - `dispatch_daily_prompts_task()` — Huey periodic task (runs once at midnight UTC); iterates all users with `push_enabled=True` and calls `schedule_daily_prompts_for_user`.
- `iceplunge/notifications/management/commands/dispatch_daily_prompts.py` — management command wrapper for manual triggering.

**Acceptance criteria:**
- Unit test: `dispatch_daily_prompts_task` does not create prompts for users with `push_enabled=False`.
- Unit test: morning prompt is scheduled at the user's `morning_window_start` in their local timezone (use `pytz` or `zoneinfo`).

---

## Phase 7 — Quality & Compliance ✅

### T7.1 Quality flag computation
**Goal:** Automatically compute and store quality flags on each completed `TaskResult`.

**Spec refs:** §18 Data Integrity (Quality Flags)

**Deliverables:**
- `iceplunge/tasks/helpers/quality.py`:
  - `flag_anticipation_bursts(trials)` → bool (3+ anticipation responses in a single task).
  - `flag_excessive_misses(trials, threshold=0.5)` → bool (> 50% of trials have no response).
  - `flag_rapid_resubmission(user, session)` → bool (another completed session within 10 minutes).
  - `flag_visibility_events(session)` → bool (> 2 interruptions logged).
  - `compute_quality_flags(user, session, task_result)` → list of flag strings.
- `TaskResultSubmitView` calls `compute_quality_flags` and appends result to `CognitiveSession.quality_flags`.

**Acceptance criteria:**
- Unit tests for each flag function, including boundary cases.
- Flags are stored as strings in the list, not booleans (e.g., `"anticipation_burst"`, `"excessive_misses"`).

---

### T7.2 Anti-gaming rate limits
**Goal:** Enforce the voluntary session rate limit.

**Spec refs:** §18 Session Limits

**Deliverables:**
- `iceplunge/tasks/helpers/rate_limits.py`:
  - `MAX_VOLUNTARY_SESSIONS_PER_HOUR` = 2 (configurable via Django setting).
  - `MAX_VOLUNTARY_SESSIONS_PER_DAY` = 8 (configurable).
  - `check_voluntary_rate_limit(user)` → `(allowed: bool, reason: str | None)`.
- `SessionStartView` calls `check_voluntary_rate_limit` before creating a session; returns a 429 response with a user-facing message if blocked.

**Acceptance criteria:**
- Unit test: third voluntary session within one hour is blocked.
- View test: blocked attempt returns 429 with a human-readable message rendered in the template.

---

## Phase 8 — Participant Dashboard ✅

### T8.1 Dashboard JSON API
**Goal:** Provide JSON endpoints that the dashboard charts consume.

**Spec refs:** §9 Participant Dashboard, §14 (access controls: participants see only their own data)

**Deliverables:**
- `iceplunge/dashboard/views.py` JSON endpoints (all login-required; return only the requesting user's data):
  - `GET /api/dashboard/rt-trend/` → `[{ date, median_rt, lapse_count }]` (one point per completed session with PVT).
  - `GET /api/dashboard/mood-trend/` → `[{ date, valence, arousal, stress, sharpness }]`.
  - `GET /api/dashboard/plunge-performance/` → `[{ proximity_bin, median_rt, n }]` (aggregated by proximity bin).
  - `GET /api/dashboard/inhibition-trend/` → `[{ date, commission_errors, go_median_rt }]` (SART).
  - `GET /api/dashboard/processing-speed-trend/` → `[{ date, correct_per_minute }]` (Digit Symbol).
- URL names: `dashboard:rt_trend`, `dashboard:mood_trend`, `dashboard:plunge_performance`, `dashboard:inhibition_trend`, `dashboard:processing_speed_trend`.

**Acceptance criteria:**
- Each endpoint returns 200 with a JSON array (empty array if no data yet).
- Unit test: endpoint only returns data for the authenticated user.

---

### T8.2 Dashboard page and charts
**Goal:** Render the participant-facing analytics dashboard.

**Spec refs:** §9 Participant Dashboard

**Deliverables:**
- `iceplunge/dashboard/views.py::DashboardView` — renders `iceplunge/templates/dashboard/dashboard.html`.
- Self-hosted Chart.js loaded from `iceplunge/static/dashboard/js/chart.min.js`.
- Four charts rendered on the dashboard page using vanilla JS + Chart.js consuming the API endpoints from T8.1:
  - Reaction time trend (line chart, x=date, y=median RT, secondary y=lapse count).
  - Mood trajectory (multi-line, one line per dimension).
  - Performance by plunge proximity (bar chart, x=proximity bin, y=median RT).
  - Inhibition error trend (line chart, x=date, y=commission errors).
- Charts only render once the page is loaded (not SSR); show a loading state while data fetches.
- **Dashboard framing:** each chart panel includes a one-sentence plain-language caption explaining what the metric means and what direction is "better" (e.g. "Lower reaction times indicate faster alertness. Your median is shown in blue."). A persistent "About this dashboard" section explains that individual session variability is normal, that partial sessions are included in trends but flagged, and that the data shown is for personal insight only and should not be used for medical decisions.
- URL name: `dashboard:index`.

**Acceptance criteria:**
- Dashboard page loads with a 200 without any JS errors in the console (manual test).
- Charts render correctly with fixture data injected via unit tests on the API endpoints. *(manual: visual chart check)*

---

## Phase 9 — Research Data Export ✅

### T9.1 Session-level CSV export
**Goal:** Produce a research-ready session-level CSV with all covariates and derived variables.

**Spec refs:** §14 Research Data Export

**Deliverables:**
- `iceplunge/export/views.py::SessionExportView` (requires `export_data` permission):
  - Accepts query params: `date_from`, `date_to`.
  - Streams a CSV response (use `StreamingHttpResponse` + `csv.writer`).
  - Columns: `pseudonymised_id`, `session_id`, `started_at`, `completed_at`, `completion_status`, `task_order`, all `derived_variables` keys flattened, all `DailyCovariate` fields for the session date, all `WeeklyCovariate` fields for the session week, mood ratings, per-task summary metrics.
  - No PII columns (no email, no name).
- `iceplunge/export/helpers/audit.py::log_export(user, export_type, date_from, date_to)` — creates an `ExportAuditLog` model entry.
- `ExportAuditLog` model in `iceplunge/export/models.py`: `user`, `export_type`, `exported_at`, `date_from`, `date_to`, `row_count`.
- URL name: `export:sessions_csv`.

**Acceptance criteria:**
- View returns 403 for users without `export_data` permission.
- CSV first row is a header row; no PII columns present.
- `ExportAuditLog` record created on each successful export.
- Unit test with 3 fixture sessions validates column count and pseudonymised_id usage.

---

### T9.2 Trial-level CSV and JSON dump exports
**Goal:** Provide granular trial-level and complete JSON exports.

**Spec refs:** §14 Research Data Export

**Deliverables:**
- `iceplunge/export/views.py::TrialExportView` (requires `export_data` permission):
  - Streams a CSV with one row per trial across all `TaskResult.trial_data` entries.
  - Columns: `pseudonymised_id`, `session_id`, `task_type`, `task_version`, `trial_index`, `stimulus_at_ms`, `response_at_ms`, `correct`, plus task-specific fields.
- `iceplunge/export/views.py::FullJsonExportView` (requires `export_data` permission):
  - Streams a JSON array of all sessions with nested task results and trials; uses `pseudonymised_id` throughout.
- URL names: `export:trials_csv`, `export:full_json`.

**Acceptance criteria:**
- Both views return 403 without permission.
- JSON export is valid JSON (parseable by `json.loads`).
- Unit test validates `pseudonymised_id` is used (not `user.id` or email).

---

## Phase 10 — Ethics & Self-Service Governance ✅

### T10.1 Data deletion flow
**Goal:** Allow participants to request and confirm full data deletion from within the app.

**Spec refs:** §19 Withdrawal and Deletion

**Deliverables:**
- `iceplunge/users/views.py::DataDeletionRequestView`:
  - GET: renders a confirmation page explaining what will be deleted.
  - POST: requires SweetAlert2 confirmation on the client side before submitting.
  - On confirmed POST: deletes `PlungeLog`, `CognitiveSession` (cascades to `TaskResult`, `MoodRating`, `SessionCovariate`), `DailyCovariate`, `WeeklyCovariate`, `BaselineProfile`, `ConsentProfile`, `NotificationProfile` for the user; flags the `User` record as `is_active=False`; queues a confirmation email via Huey.
- `iceplunge/users/tasks.py::send_deletion_confirmation_email(user_email)` — Huey task sends confirmation.
- `iceplunge/users/helpers/deletion.py::delete_participant_data(user)` — contains all deletion logic; called by the view.
- Template at `iceplunge/templates/users/data_deletion.html`.
- URL name: `users:data_deletion`.

**Acceptance criteria:**
- Unit test: `delete_participant_data` removes all linked records and deactivates the user.
- Unit test: `User` record itself is not hard-deleted (retained for audit); `is_active=False`.
- Confirmation email task is enqueued (not sent synchronously).

---

### T10.2 Notification opt-out
**Goal:** Participants can disable push notifications without ending participation.

**Spec refs:** §19 Withdrawal and Deletion (first bullet)

**Deliverables:**
- `iceplunge/notifications/views.py::NotificationPreferencesView`:
  - GET: renders form showing current `push_enabled`, `morning_window_start`, `evening_window_start`.
  - POST: updates `NotificationProfile`; HTMX-aware.
- Partial template at `iceplunge/templates/notifications/partials/_notification_prefs.html`.
- URL name: `notifications:preferences`.

**Acceptance criteria:**
- Setting `push_enabled=False` causes `should_send_scheduled_prompt` (T6.3) to return False.
- Unit test for the above.

---

## Phase 11 — Capacitor Wrapper ✅

### T11.1 Capacitor project setupit
**Goal:** Wrap the Django web app in a Capacitor container for iOS and Android.

**Spec refs:** §2 Mobile Delivery

**Deliverables:**
- `capacitor/` directory at project root with `capacitor.config.ts` pointing `webDir` at the Django dev server (for local) or a production URL.
- `package.json` with `@capacitor/core`, `@capacitor/ios`, `@capacitor/android`, `@capacitor/push-notifications`.
- `capacitor/` `.gitignore` excluding `ios/`, `android/`, `node_modules/`.
- `README` section (in existing README or new `capacitor/README.md`) describing how to build for iOS and Android.
- OneSignal Capacitor SDK (`onesignal-capacitor`) added; JS init snippet documented.

**Acceptance criteria:**
- `npx cap sync` runs without error after `npm install`.
- `capacitor.config.ts` is valid TypeScript; `appId` and `appName` are set.

---

## Dependency Summary

```
T0.1 → T0.2 → T0.3
T0.1 → T1.1 → T1.2 → T1.3 → T1.4 → T1.5
T1.2 → T2.1 → T2.2
T1.3, T1.5 → T3.1 → T3.2
T1.3, T1.4 → T4.1 → T4.2 (all task JS depends on T4.2)
T4.1, T4.2 → T5.1 → T5.5
T2.2 → T6.1 → T6.2 → T6.3
T4.3 → T7.1 → T7.2
T5.1–T5.5 → T8.1 → T8.2
T1.4, T1.5 → T9.1 → T9.2
T1.1–T1.5 → T10.1
T6.1 → T10.2
T0.1 → T11.1
```

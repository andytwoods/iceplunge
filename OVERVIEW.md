# Ice Plunge Cognitive Research Platform – Build Specification

---

# 1. Purpose

A research-grade mobile platform to investigate the acute and longitudinal cognitive effects of cold plunging.

Primary research question:
Does cold plunge frequency influence cognitive performance, and is the relationship linear, U-shaped, or subject to adaptation over time?

The platform must:

* Support high-frequency repeated cognitive assessment.
* Link performance precisely to plunge timing and frequency.
* Provide participant-facing analytics dashboards.
* Be statistically structured for multilevel modelling.

---

# 2. Architecture

## Mobile Delivery

* Web-based application wrapped with **Capacitor** (iOS + Android).
* Native push notifications via **OneSignal** (APNs + FCM).
* Web UI delivered inside the Capacitor container.

## Backend

* Django-based backend.
* Responsibilities:

  * Authentication and user management.
  * Plunge logging.
  * Cognitive task data storage (trial-level + session-level).
  * Push scheduling logic.
  * Randomisation logic.
  * Research data export.

## Frontend Stack

* Django templates + HTMX for modular loading.
* Each cognitive task is a self-contained module:

  * Dedicated template/partial.
  * Task-specific JS.
  * Standardised result payload schema.

---

# 3. Task Modularity and Randomisation

## Modularity Principle

Each cognitive task is a fully self-contained module. No task may depend on the internals of another task. Shared behaviour (timing utilities, result submission, interruption detection) lives in a shared library (`tasks/static/tasks/js/task_core.js`); tasks call into it but do not modify it.

---

## Backend Task Registry

Each task type is registered in a central Python dictionary / Django app config:

```
TASK_REGISTRY = {
    "pvt":          { "label": "PVT",           "version": "1.0", "battery": "core" },
    "sart":         { "label": "SART",          "version": "1.0", "battery": "core" },
    "flanker":      { "label": "Flanker",       "version": "1.0", "battery": "rotating" },
    "digit_symbol": { "label": "Digit Symbol",  "version": "1.0", "battery": "rotating" },
    "mood":         { "label": "Mood Rating",   "version": "1.0", "battery": "core" },
}
```

* The registry is the single source of truth for task type strings used in `TaskResult.task_type`.
* Adding a new task requires a registry entry; the server rejects `TaskResult` submissions with unregistered `task_type` values.
* Version is bumped when stimulus logic or scoring changes in a way that affects comparability.

---

## Template Contract

Each task module has exactly one partial template at:

```
tasks/templates/tasks/partials/_<task_type>.html
```

The partial must:

* Contain a single root element: `<div id="task-<task_type>" class="task-module" data-task-type="<task_type>">`.
* Embed or reference only its own task JS (no inline scripts touching other task DOM nodes).
* Include a `<div class="task-result-target"></div>` where the HTMX result confirmation is swapped in on submission.
* Not assume any DOM state outside its own root element.

---

## JavaScript Interface Contract

Every task JS file (`tasks/static/tasks/js/<task_type>.js`) must export exactly this interface:

```js
{
  init(config),      // called once when the partial is loaded; config passed from server
  pause(),           // called on visibility/background event; must freeze all timers
  resume(),          // called on foreground return; restores timers
  abort(reason),     // called on timeout, navigation away, or manual stop
}
```

* `init(config)` receives a plain object from the server: `{ sessionId, taskVersion, seed, durationMs, ... }`.
* All timing uses `performance.now()`; wall-clock timestamps are computed as `Date.now()` at capture time.
* The task calls `TaskCore.submit(payload)` (from `task_core.js`) to POST results — it never constructs its own fetch/HTMX request.
* The task must call `TaskCore.logEvent(type, detail)` for every interruption, anticipation burst, or anomaly.

---

## Standardised Result Payload Schema

`TaskCore.submit()` enforces this envelope; all fields are mandatory:

```json
{
  "session_id":    "<uuid>",
  "task_type":     "<registry key>",
  "task_version":  "1.0",
  "started_at":    "<ISO-8601 UTC>",
  "ended_at":      "<ISO-8601 UTC>",
  "duration_ms":   60000,
  "input_modality":"touch|keyboard",
  "interruptions": [ { "type": "background", "offset_ms": 12400 } ],
  "trials": [
    { "trial_index": 0, "stimulus_at_ms": 1234.5, "response_at_ms": 1456.2, "correct": true, ... }
  ],
  "summary": { }
}
```

* `trials` contains one object per stimulus/response event; schema is task-specific but must include `trial_index`, `stimulus_at_ms`, `response_at_ms` (null if no response), and `correct` (bool or null).
* `summary` contains pre-computed task-specific metrics (e.g. median RT, lapse count); the server re-derives these independently and flags discrepancies.
* The server validates the envelope schema and rejects malformed payloads with a 422 response.
* Partial sessions (interrupted before completion) are **not** saved — the server enforces this; the client must not submit unless the task ran to its natural end.

---

## Lifecycle Event Handling

Every task must handle these browser events via `TaskCore` hooks:

| Event | Required behaviour |
| --- | --- |
| `visibilitychange` (hidden) | Call `pause()`; log interruption |
| `visibilitychange` (visible) | Call `resume()` |
| `pagehide` / `beforeunload` | Call `abort("navigated_away")` |
| Session timer expiry | Call `abort("timeout")` |
| Manual stop button | Call `abort("manual_abort")` |

---

## Randomisation

Within each prompted session:

* Randomise order of core tasks.
* If a rotating module is included, randomise its position.
* Store:

  * Session ID.
  * Task order.
  * Task version identifiers.
  * Random seed (mandatory, for audit reproducibility).

---

# 4. Cognitive Assessment Battery

## Core Battery (Most Prompts)

### 1-Minute Psychomotor Vigilance Task (PVT)

Duration: 60 seconds.

Outcomes:

* Median reaction time.
* Lapse count (>500 ms).
* Reaction time variability.
* Anticipations (<100 ms).

Construct:

* Tonic alertness / vigilance.

Rationale:

* Based on validated brief PVT literature (e.g., PVT-B and adaptive-duration research).
* Short duration acceptable due to repeated-measures multilevel modelling.

---

### SART-Style Sustained Attention Task (60–90 seconds)

Frequent go responses with rare no-go targets (~10–15%).

Outcomes:

* No-go commission errors.
* Go RT (median/trimmed mean).
* RT variability.
* Optional post-error slowing.

Construct:

* Sustained attention + inhibitory control.

---

### Mood and Subjective State (Every Prompt)

5-point Likert scales with face-based anchors:

* Valence.
* Arousal/Energy.
* Stress/Tension.
* Mental sharpness.

Completion time target: <15 seconds.

---

## Rotating Modules (Max 1 Per Day)

### Flanker Task (Selective Attention)

Duration: 60–90 seconds.

Outcomes:

* Conflict effect (incongruent – congruent RT).
* Accuracy by condition.

Construct:

* Executive control / selective attention.

---

### Processing Speed (Digit Symbol–Style)

Duration: 60–90 seconds.

Outcomes:

* Correct responses per minute.
* Error rate.

Construct:

* Processing speed / perceptual-motor integration.

---

# 5. Plunge Logging

Each plunge entry includes:

* Timestamp.
* Duration.
* Water temperature.
* Measured vs estimated indicator.
* Immersion depth (waist/chest/neck).
* Context (plunge pool/bath/lake/sea/cryotherapy/other).
* Breathing technique.
* Perceived intensity / perseverance effort (5-point scale: "How hard was it to persevere?").
* Pre-plunge hot treatment (optional): type (sauna / steam room) and duration in minutes.
* Exercise session (optional): timing (before / after the plunge), type (cardio / weights), and duration in minutes.

---

# 6. Covariates

## Baseline

* Age.
* Gender.
* Height.
* Body weight (baseline only).
* Derived BMI.
* Years of cold plunge experience.
* Handedness.

## Per Session

* Caffeine since last session.
* Time since last meal.
* Mood scales.
* Mental sharpness.

## Daily

* Sleep duration (hours, 0.5-step).
* Sleep quality (5-point: Poor – Excellent).
* Alcohol last 24h (yes/no).
* Exercise today (yes/no).

Captured via the "More information" section on the plunge log page and after each cognitive session. Stored in `DailyCovariate` (one record per user per date; updated if the form is submitted again the same day).

## Weekly

* Gastrointestinal discomfort severity (5-point: None – Severe).
* Optional GI symptom checkboxes (bloating, cramps, nausea, diarrhea, constipation, reflux).
* Current illness status (yes/no).

Captured via the same "More information" section. Stored in `WeeklyCovariate` (one record per user per week; updated if re-submitted).

---

# 7. Derived Variables (Server-Computed)

* Time since most recent plunge.
* Proximity bins (pre, 0–15m, 15–60m, 1–3h, >3h).
* Same-day plunge count.
* Rolling 7/14/30-day plunge frequency.
* Typical weekly plunge frequency (derived).
* Long-term frequency trends.
* Season indicators.

No self-report used where behavioural logs suffice.

---

# 8. Statistical Framework

Primary analytic approach:

* Multilevel (hierarchical) regression.

Structure:

* Repeated sessions nested within individuals.
* Random intercepts.
* Random slopes for proximity and frequency.
* Non-linear terms (quadratic/cubic) to test U-shaped relationships.

Focus:

* Acute within-person effects.
* Dose-response patterns.
* Adaptation over calendar time.

Likert scales stored as ordinal but modelled as appropriate.

---

# 9. Participant Dashboard

Participants can view:

* Reaction time trends.
* Lapse trends.
* Inhibition error rates.
* Processing speed metrics.
* Mood trajectories.
* Performance relative to plunge proximity.

Visualisations:

* Time-series plots.
* Pre–post comparisons.
* Frequency vs performance curves.

Designed to maximise engagement and transparency.

---

# 10. Reliability Strategy

* Native push via OneSignal.
* Local notifications for fixed schedules if required.
* High-frequency sampling compensates for short task duration.
* Device metadata captured for modelling (OS, device class).

---

# 11. Notification & Prompting Schedule

## Prompt Types

* **Reactive prompts** — triggered automatically after each logged plunge.
  * First prompt: 15–30 minutes post-plunge.
  * Second prompt: 2–3 hours post-plunge.
* **Scheduled prompts** — fixed daily assessments independent of plunge activity, to capture baseline cognitive state.
  * Default: morning (within 60 minutes of waking) and evening (18:00–21:00 local time).
* Participants may configure their preferred scheduled prompt windows during onboarding.

## Rate Limits

* Maximum 5 prompts per 24-hour period (configurable by study admin).
* Minimum 45-minute gap between any two prompts.
* Reactive prompts take priority over scheduled prompts within the daily cap.

## Prompt Delivery

* Primary delivery: OneSignal push notification (APNs + FCM).
* Fallback: local notification scheduled on-device for participants with push disabled.
* Prompt delivery timestamp, open timestamp, and latency are logged (see Section 16).

---

# 12. Onboarding & Baseline Assessment

## Registration Flow

1. Account creation via django-allauth (email/password, Google, or GitHub).
2. Email verification required before data collection begins.
3. In-app consent flow (see Section 19) — must be completed before proceeding.

## Baseline Covariate Collection

* Collected once at registration; editable by participant in profile settings.
* Fields: age, gender, height, weight (→ BMI derived server-side), handedness, years of cold plunge experience.
* Stored as a separate `BaselineProfile` record linked to the user.

## Task Familiarisation

* Before the first live session, participants complete a short practice block for each core task (PVT, SART).
* Practice block data is flagged and excluded from analysis.
* Familiarisation sessions do not count toward the daily prompt cap.
* First 3–5 live sessions per task are additionally flagged as acclimatisation (see Section 17).

---

# 13. Data Models & Storage Schema

## Core Entities

| Model | Key Fields |
| --- | --- |
| `User` | allauth-managed; pseudonymised export ID |
| `BaselineProfile` | age, gender, height, weight, BMI, handedness, plunge_years |
| `PlungeLog` | user, timestamp, duration, water_temp, temp_measured, immersion_depth, context, breathing_technique, perceived_intensity (perseverance effort), pre_hot_treatment (sauna/steam_room, nullable), pre_hot_treatment_minutes (nullable), exercise_timing (before/after, nullable), exercise_type (cardio/weights, nullable), exercise_minutes (nullable) |
| `PromptEvent` | user, scheduled_at, sent_at, opened_at, prompt_type (reactive/scheduled), linked_plunge |
| `CognitiveSession` | user, prompt_event, started_at, completed_at, task_order, random_seed, device_meta, completion_status, quality_flags |
| `TaskResult` | session, task_type, task_version, started_at, completed_at, trial_data (JSON), summary_metrics (JSON), session_index_overall, session_index_per_task |
| `MoodRating` | session, valence, arousal, stress, sharpness |
| `DailyCovariate` | user, date, sleep_duration_hours, sleep_quality (1–5), alcohol_last_24h, exercise_today |
| `WeeklyCovariate` | user, week_start, gi_severity (1–5), gi_symptoms (JSON list), illness_status |
| `SessionCovariate` | session (OneToOne), caffeine_since_last_session, minutes_since_last_meal, cold_hands, wet_hands |

## Key Relationships

* `CognitiveSession` → `PromptEvent` (nullable; sessions may be voluntary).
* `TaskResult` → `CognitiveSession` (one session, many task results).
* `PlungeLog` → `User` (many per user; used to compute derived variables server-side).

## Derived Variables

Computed and cached server-side at session creation time (see Section 7); stored alongside session record for analytical reproducibility.

---

# 14. Research Data Export

## Export Formats

* **Session-level CSV**: one row per cognitive session; includes all covariates, derived variables, and summary metrics.
* **Trial-level CSV**: one row per stimulus/response event; linked to session via session ID.
* **Full JSON dump**: complete nested export (sessions → task results → trials) for custom analysis pipelines.

## Anonymisation

* All exports use a stable pseudonymised participant ID (not the internal database PK or any PII).
* Timestamps exported in UTC.
* Direct identifiers (name, email) never included in any export.
* Export pipeline reviewed against retention policy before each data release.

## Access Controls

* Research exports available to superusers and staff with explicit `export_data` permission.
* All export events logged (who, when, what date range).
* Participants cannot access raw trial-level data of other participants via the dashboard.

---

# 15. Timing Precision & Device/Context Effects

## Reaction Time Measurement

* All RT timestamps recorded client-side using high-resolution timing (e.g., `performance.now()` semantics).
* Task stimuli presentation aligned to browser rendering where feasible (e.g., frame-synchronised scheduling).
* Input modality captured (touch vs keyboard) and treated as a modelling covariate.

## Device and Browser Metadata

Captured automatically per session:

* OS, device model/class (where available), browser engine/webview version.
* Screen refresh rate proxy/estimate where feasible.
* Viewport size and orientation.

## Context and Validity Events

Logged during tasks:

* App background/foreground transitions.
* Visibility changes.
* Orientation changes.
* Significant performance/jank indicators where feasible.

---

# 16. Compliance & Adherence Logging

Tracked per prompt and session:

* Notification sent timestamp.
* Notification opened timestamp (if available).
* Task session start timestamp.
* Task session completion timestamp.
* Prompt-to-start latency.
* Completion status (complete vs abandoned).

Adherence metrics derivable:

* % prompts responded to.
* Median response latency.
* Distribution of completions across the day.

---

# 17. Practice Effects & Acclimatisation

* Early sessions flagged as acclimatisation to reduce learning-contamination (parameter to be set; e.g., first 3–5 sessions per task).
* Store per-user task exposure counters:

  * Session index overall.
  * Session index per task module.
* Statistical models include practice terms (e.g., session index, log(session index), or smooth terms) to account for learning and habituation.

---

# 18. Data Integrity & Anti-Gaming Safeguards

## Session Limits

* Rate-limit voluntary cognitive sessions to prevent excessive repeated sampling (policy configurable; e.g., max N per hour/day).

## Interruption and Backgrounding

* Maintain the existing rule: partial task data not saved.
* Additionally log:

  * interruption reason (backgrounded, navigated away, timeout, manual abort).

## Quality Flags (Logged, Not Used to Block)

* Flag sessions with:

  * repeated ultra-fast responses (anticipation bursts).
  * excessive missing/timeout responses.
  * rapid repeated sessions within short windows.
  * multiple visibility/background events.

Quality flags are stored for downstream sensitivity analyses (include/exclude).

---

# 19. Ethics, Consent & Data Governance

## Consent

* In-app consent flow required before any data collection.
* Consent includes:

  * purpose of study.
  * what data are collected.
  * risks/benefits.
  * withdrawal options.
  * contact details.

## Withdrawal and Deletion

* Participants can opt out of notifications at any time via in-app settings; this does not end participation.
* Participants can request full data deletion via an in-app self-service flow or by contacting the research team.
* On deletion request:
  * All raw linked records (plunge logs, cognitive sessions, task results, covariates) are permanently deleted.
  * The pseudonymised participant ID is removed from any exportable datasets.
  * Aggregate or anonymised results already included in published analyses are not retroactively altered, in line with standard research ethics practice; this is disclosed in the consent flow.
* Deletion requests are actioned within 30 days and confirmed to the participant by email.

## Data Protection

* Data stored securely on the Django backend.
* Pseudonymised participant identifiers used for export.
* Timestamps stored in UTC.
* Retention period and access controls documented.

---

This document represents the build-ready specification for implementation.

---

# 20. Sponsor This Research

## Purpose

A homepage section inviting individuals and organisations to financially support the project. Funds cover server costs; surplus goes toward hiring researchers and developers to extend the platform.

## Tiers

| Tier | Recognition | Suggested amount |
| --- | --- | --- |
| **Individual** | Name listed in text | ~£5 / month |
| **Organisation** | Logo displayed, linked to sponsor's website | ~£50 / month |

## Payment Routes

* **Individuals** — GitHub Sponsors link (self-serve).
* **Organisations** — Contact form on the homepage; sponsorship agreed offline.

## Onboarding

* Sponsors email the research team after paying to provide their name / logo / URL.
* The research team adds them manually via Django admin.

## Data Model

A `Sponsor` model with fields: `name`, `logo` (optional image), `url` (optional, org only), `tier` (`individual` / `organisation`), `is_active` (boolean).

## Homepage Placement

Prominent mid-page section, rendered from the `Sponsor` model. Suggested amounts and both payment routes (GitHub Sponsors button + contact form / mailto link for orgs) displayed within the section.

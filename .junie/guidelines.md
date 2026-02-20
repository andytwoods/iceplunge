# Django Guidelines

You are an expert in Python, Django, and scalable web apps. Write secure, maintainable, performant code.

## Python
- Follow PEP 8 (120 char limit), double quotes, `isort`, f-strings.

### Exception handling
- **Never use catch-all exceptions**:
  - Do not use bare `except:` or `except Exception:` anywhere in the codebase.
  - Always catch the **most specific** exception you can genuinely handle.
  - If meaningful recovery is not possible, let the exception propagate so it fails loudly.
  - Use logging instead of `print()` when reporting errors.
- **Static analysis**
  - Configure linting (e.g. Ruff/flake8) to *error on*:
    - bare `except:`
    - `except Exception:`
    - unused exception variables

## Project Scaffold

- **All Django projects start from [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django).**
  ```
  cookiecutter gh:cookiecutter/cookiecutter-django
  ```
- Do **not** hand-roll a project structure; the cookiecutter output is the baseline.
- The cookiecutter already provides — do not recreate these:
  - Split settings (`config/settings/base.py`, `local.py`, `production.py`).
  - Custom `User` model in the `users` app (`users/models.py`), with `AUTH_USER_MODEL = "users.User"` already set.
  - `requirements/` split (`base.txt`, `local.txt`, `production.txt`).
  - Whitenoise for static files.
  - Basic `Makefile` and `docker-compose` stubs.
- When referencing the User model in code, always use `get_user_model()` — never import `User` directly.
- New user-related fields and profile models belong in the `users` app, extending what cookiecutter already created.

## Django
- Use built-ins before third-party.
- Prioritise security; use ORM over raw SQL.
- Use signals sparingly.

## Authentication
- Use **django-allauth** for authentication. No custom auth backends.
- Social login providers: **Google** and **GitHub**.
- Keep email/password registration as a fallback.
- Configure allauth to require email verification.

## User Impersonation
- Use **django-hijack** to allow admins to impersonate any user.
- Configure hijack to appear in the Django admin (hijack button on user list/detail).
- Only superusers and staff with explicit permission should be able to hijack.
- Show a visible warning banner when a session is hijacked so it's never mistaken for a real user session.

## Models
- Always add `__str__`.
- Use `related_name` when helpful.
- `blank=True` for forms, `null=True` for DB.

## Views
- Validate/sanitise input.
- Prefer `get_object_or_404`.
- Paginate lists.

## URLs
- Descriptive names, end with `/`.

## Frontend / CSS
- Use **Bulma** as the CSS framework. No Bootstrap, Tailwind, or other CSS frameworks.
- Load Bulma via CDN or pip (`django-bulma`) — keep it consistent across the project.
- Use Bulma classes in templates; avoid writing custom CSS unless Bulma has no suitable class.

## Frontend / UI JavaScript preferences
- Use **SweetAlert2** for modal dialogs/alerts/confirmations (instead of `alert()`, `confirm()`, or rolling our own modals).
- **Avoid CDNs for frontend dependencies**: prefer self-hosting JS/CSS libraries in our static files (or bundling them) so we control availability and CSP.
  - **Exception:** very large dependencies (e.g. **pyiodine**) may be loaded from a CDN when justified.

## HTMX and JavaScript — when to use which
- Use **htmx** for dynamic partial updates. No React, Vue, or other JS frameworks.
- **Same-endpoint pattern:** HTMX requests hit the same URL as the full page. The view detects HTMX via `request.headers.get("HX-Request")` and returns a partial template (fragment) instead of the full page.
- Do **not** create separate URL routes for HTMX endpoints.

### HTMX is the default for:
- Form submissions (consent, surveys, profile intake).
- Session flow transitions (challenge → reflection questions → "another?" prompt → next challenge).
- Any server-rendered content swap that would otherwise be a full page reload.

### Vanilla JS is used only for:
- **Pyodide / code editor** — CodeMirror, Web Worker execution, timer, telemetry capture. This is inherently JS-driven and HTMX doesn't apply.
- **Chart rendering** — Chart.js/Plotly.js fetching JSON from API endpoints. HTMX doesn't help here.

### JSON API endpoints are acceptable only for:
- Aggregate chart data consumed by Chart.js/Plotly.js (e.g. `/api/stats/`).
- Pyodide test result submission (client posts JSON after local execution).
- Do **not** create JSON endpoints for anything that could be an HTMX partial swap instead.

## Templates
- **App-local templates only.** Every app's templates live in `<app>/templates/<app>/`, never in a global `templates/` directory.
  - Base templates (`base.html`, `navbar.html`, etc.) live in the `pages` app: `pages/templates/base.html`.
  - All other apps extend `base.html`.
  - Example: `challenges/templates/challenges/challenge_detail.html`
- **HTMX partials** live in a `partials/` subdirectory within the app's template directory.
  - Prefix partial filenames with `_` (e.g. `_challenge_detail.html`).
  - Example: `challenges/templates/challenges/partials/_challenge_detail.html`
- Use template inheritance. Keep logic minimal.
- Always `{% load static %}`, enable CSRF.

## Forms
- Prefer ModelForms.
- Use crispy-forms with the Bulma template pack (`crispy-bulma`).

## Settings
- Use env vars, never commit secrets.
- Settings are split into `base.py` / `local.py` / `production.py` by the cookiecutter scaffold — do not collapse them.
- **Local dev (`local.py`):** use SQLite — no need for PostgreSQL locally.
- **Production (`production.py`):** use PostgreSQL.
- **Error tracking:** use **Rollbar** in production (`django-rollbar`). Configure via `ROLLBAR_ACCESS_TOKEN` env var. Do not enable in local dev.

## Database
- Always use migrations.
- Optimise queries (`select_related`, `prefetch_related`).
- Index frequent lookups.

## Background tasks / Queue
- Prefer **Huey** for background jobs.
- **Never use Celery** in this codebase (no Celery configs, workers, brokers, or Celery-specific task decorators).
- When adding async work:
  - implement tasks using Huey’s decorators and configuration;
  - keep business logic in helper modules per the “Tasks” section below.

## Tasks (Framework-Agnostic)

### Task layout
- Each app’s `tasks.py` must **only** contain task-decorated functions for the chosen task-queue system.
- No business logic, utility functions, or classes should be placed in `tasks.py`.
- Task functions should:
  - accept and validate raw input;
  - call helper functions that contain the actual business logic;
  - handle only queue-specific concerns such as scheduling, retries, or metadata.

### Task helpers
- Create a dedicated module for task-related logic, e.g. `helpers/task_helpers.py` (project-wide or per-app).
- All business/domain logic used by tasks must live in `task_helpers.py`, not in `tasks.py`.
- Helper functions should be:
  - reusable by views, management commands, and tasks;
  - clear about side-effects;
  - written to be as idempotent as reasonably possible (safe for retries).


## Testing
- Write unit tests for new features.
- Cover both success and failure paths.
- Never hard-code URL paths (e.g. `"/users/123/"`) in assertions.
  - Use `django.urls.reverse()` with named routes (e.g. `reverse("users:detail", kwargs={"pk": user.pk})`).
  - For redirects that depend on the current request URL, use `request.path` (or `request.get_full_path()`) in expectations.

# Cold Cognition Project — Ice Plunge

A community-led citizen-science platform that captures repeated cognitive measurements from cold-water immersion practitioners before and after plunges, building a longitudinal dataset to study the acute and chronic effects of cold-water immersion on cognition.

---

## What is this?

Cold-water immersion (ice plunging, wild swimming, cold showers) has become popular for its reported mental and physical benefits. This platform lets participants:

1. **Log plunges** — record water temperature, duration, immersion depth, perceived intensity, and context
2. **Run cognitive tests** — complete a short battery of validated tasks immediately before and after plunging
3. **Track progress** — view personal dashboards showing how cognition changes over time and in relation to plunge parameters

All data is contributed anonymously to a shared research dataset, enabling longitudinal citizen-science analysis at scale.

---

## Cognitive task battery

Each session takes ~5 minutes and presents five tasks in randomised order:

| Task | Name | What it measures | Duration |
|------|------|-----------------|----------|
| `pvt` | Psychomotor Vigilance Task | Sustained attention / reaction time | ~60 s |
| `sart` | Sustained Attention to Response Task | Inhibitory control | ~75 s |
| `flanker` | Eriksen Flanker Task | Selective attention / conflict resolution | ~75 s |
| `digit_symbol` | Digit Symbol Coding | Processing speed / working memory | ~75 s |
| `mood` | Mood Rating | Subjective affect (mood, energy, stress, clarity) | Self-paced |

The Mood Rating task uses four validated 7-point bipolar scales based on the Feeling Scale (FS), Felt Arousal Scale (FAS), Stress NRS-11, and Stanford Sleepiness Scale.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5 (cookiecutter-django scaffold), Python 3.13 |
| Database | SQLite (local dev) / PostgreSQL (production) |
| Auth | django-allauth — email, Google, GitHub; consent-gated middleware |
| Frontend | Bulma CSS, HTMX (partial page updates), vanilla JS task runners |
| Task queue | Huey (Redis-backed, used for notifications) |
| Mobile | Capacitor 6 — wraps Django WebView for iOS/Android |
| Push notifications | OneSignal (via Capacitor plugin) |
| Error tracking | Rollbar (production only) |
| Deployment | Appliku (Docker-based PaaS) |

---

## Project structure

```
iceplunge/
├── users/           # Custom user model, consent middleware
├── tasks/           # Cognitive session management, task registry, JS runners
├── plunges/         # Plunge logging (PlungeLog model)
├── covariates/      # Pre-session covariate form (sleep, caffeine, etc.)
├── dashboard/       # Personal stats and charts
├── notifications/   # OneSignal push notification preferences
├── export/          # Data export for researchers
├── pages/           # Static pages (home, settings, app home)
├── static/
│   ├── tasks/js/    # Task runners (pvt.js, sart.js, flanker.js, etc.)
│   ├── css/         # Bulma, project overrides, Capacitor native styles
│   └── app/css/     # Native app home screen styles
└── templates/
    ├── base.html    # Base template with Capacitor native header injection
    └── app/home.html # Standalone native app home screen

capacitor/           # Capacitor mobile shell
├── android/         # Android project (open in Android Studio)
├── assets/          # Icon and splash source images (1024×1024, 2732×2732)
└── capacitor.config.ts
```

---

## Local development

### Prerequisites

- Python 3.13+, [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+ (for Capacitor/mobile work)
- Redis (optional — only needed for Huey task queue)

### Setup

```bash
# Clone and install dependencies
git clone <repo-url>
cd iceplunge

# Create local settings (copy and edit)
cp config/settings/local.example.py config/settings/local.py

# Install Python dependencies
uv sync

# Run database migrations
uv run python manage.py migrate

# Create a superuser
uv run python manage.py createsuperuser

# Start the development server
uv run python manage.py runserver
```

Visit `http://localhost:8000/`. Sign up, complete the consent form, then start a cognitive session.

The native app home screen is at `http://localhost:8000/app/` — it works in a browser too.

### Running tests

```bash
uv run pytest
```

To run with coverage:

```bash
uv run coverage run -m pytest
uv run coverage html
open htmlcov/index.html
```

### Type checking

```bash
uv run mypy iceplunge
```

---

## Mobile app (Capacitor)

The `capacitor/` directory contains the iOS/Android shell. It wraps the Django WebView with a native teal header bar, safe-area handling, and OneSignal push notifications.

### Android emulator

```bash
# Sync web assets and config
cd capacitor
CAPACITOR_HOST=10.0.2.2 npx cap sync android

# Open in Android Studio
npx cap open android
```

> `10.0.2.2` is the Android emulator's loopback address to the host machine. For a real device on your LAN, set `CAPACITOR_HOST` to your machine's IP.

### iOS simulator

```bash
cd capacitor
npx cap sync ios
npx cap open ios
```

### Icon and splash screen

Source files live in `capacitor/assets/`:

| File | Size | Purpose |
|------|------|---------|
| `icon-only.png` | 1024×1024 | Launcher icon (foreground + background composite) |
| `icon-foreground.png` | 1024×1024 | Adaptive icon foreground layer |
| `icon-background.png` | 1024×1024 | Adaptive icon background (`#1a9e7a` teal) |
| `splash.png` | 2732×2732 | Splash screen source |

To regenerate platform assets after changing source images:

```bash
cd capacitor
npx @capacitor/assets generate
```

---

## Deployment

The app is deployed via [Appliku](https://appliku.com/) using Docker. Configuration is in `appliku.yaml`.

Key environment variables:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `ONESIGNAL_APP_ID` | OneSignal app ID for push notifications |
| `ONESIGNAL_REST_API_KEY` | OneSignal REST API key |
| `ROLLBAR_ACCESS_TOKEN` | Rollbar error tracking token |
| `REDIS_URL` | Redis URL for Huey task queue |

---

## Consent and ethics

All participants explicitly consent before any data is collected. The consent middleware (`ConsentRequiredMiddleware`) blocks access to all research pages until consent is recorded. Participants can delete their account and all associated data at any time from the Settings page.

---

## License

MIT

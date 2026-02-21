# Ice Plunge — Capacitor Wrapper

This directory contains the Capacitor configuration for building the Ice Plunge
web app as a native iOS and Android application.

---

## Prerequisites

- Node.js 18+
- Xcode 15+ (for iOS)
- Android Studio (for Android)
- `npx` available on PATH

---

## Setup

```bash
cd capacitor
npm install
```

---

## Development (Django dev server)

Start the Django backend first:

```bash
cd ..
uv run python manage.py runserver 0.0.0.0:8000
```

Then sync and open the native project:

```bash
cd capacitor
npx cap sync
npx cap open ios      # opens Xcode
npx cap open android  # opens Android Studio
```

In dev mode, `capacitor.config.ts` sets `server.url` to `http://localhost:8000`
so the app loads directly from Django — no static build step needed.

---

## Production Build

1. Build a Django static export (or deploy Django and configure `server.url` to
   your production domain in `capacitor.config.ts`).
2. Copy the built web assets into `capacitor/www/`.
3. Run `npx cap sync` to copy assets into native projects.
4. Archive and sign via Xcode (iOS) or Gradle (Android).

---

## OneSignal Push Notifications

### SDK integration

The `onesignal-capacitor` package is included in `package.json`.

Initialise OneSignal in your app's JS entry point (e.g. loaded at the bottom of
`base.html` when running inside Capacitor):

```js
import OneSignal from "capacitor-onesignal";

// Replace with your OneSignal App ID (set via ONESIGNAL_APP_ID env var on Django).
const ONESIGNAL_APP_ID = "YOUR_ONESIGNAL_APP_ID";

async function initPush() {
  await OneSignal.setAppId(ONESIGNAL_APP_ID);

  // Request permission (iOS will prompt the user; Android 13+ prompts automatically).
  const { value: accepted } = await OneSignal.requestPermission();

  if (accepted) {
    // Register the device with our Django backend so we can target push
    // notifications at this user.
    const { userId } = await OneSignal.getDeviceState();
    if (userId) {
      await fetch("/notifications/register-device/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "",
        },
        credentials: "same-origin",
        body: JSON.stringify({ player_id: userId }),
      });
    }
  }
}

// Run after Capacitor is ready.
document.addEventListener("deviceready", initPush, false);
```

### Django side

The server-side endpoint that receives `player_id` is already implemented at:

```
POST /notifications/register-device/
```

See `iceplunge/notifications/views.py::RegisterDeviceView`.

The `ONESIGNAL_APP_ID` and `ONESIGNAL_API_KEY` values are read from environment
variables — set them in your `.env` file or deployment secrets.

---

## Notes

- Native `ios/` and `android/` project directories are git-ignored; regenerate
  them with `npx cap add ios` / `npx cap add android` after `npm install`.
- `node_modules/` and `www/` are also git-ignored.

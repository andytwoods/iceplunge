import { CapacitorConfig } from "@capacitor/cli";

const isDev = process.env.NODE_ENV !== "production";

// For Android emulator, set CAPACITOR_HOST=10.0.2.2 (emulator loopback to host).
// For a real device on the same network, set CAPACITOR_HOST to your machine's LAN IP.
// Default is localhost (works for iOS Simulator and browser-based testing).
const host = process.env.CAPACITOR_HOST || "localhost";

const config: CapacitorConfig = {
  appId: "com.iceplunge.app",
  appName: "Ice Plunge",
  // webDir is relative to this config file's location (capacitor/).
  // Point to a built static export dir in production; in dev we use the Django
  // dev server via `server.url` instead.
  webDir: "www",
  server: isDev
    ? {
        // Forward all requests to the local Django dev server so you can test
        // inside the Capacitor shell without a build step.
        // Opens /app/ directly so Apple sees meaningful bundled native content.
        url: `http://${host}:8000/app/`,
        cleartext: true,
      }
    : undefined,
  plugins: {
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
};

export default config;

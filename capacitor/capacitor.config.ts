import { CapacitorConfig } from "@capacitor/cli";

const isDev = process.env.NODE_ENV !== "production";

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
        url: "http://localhost:8000",
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

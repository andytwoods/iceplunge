/**
 * task_core.js — Shared JS library for all cognitive task modules.
 *
 * Exported as window.TaskCore.  Each task module calls TaskCore.init() once,
 * then registers itself via TaskCore.registerTask(), and submits results via
 * TaskCore.submit().
 *
 * Relies on two globals set by the session_task.html template:
 *   window.TASK_SUBMIT_URL  — URL for tasks:submit_result
 *   window.SESSION_META_URL — URL for tasks:session_meta
 */
(function () {
  "use strict";

  let _sessionId = null;
  let _csrfToken = null;
  let _initPerfTime = null;   // performance.now() captured at init
  let _interruptions = [];    // in-memory log, flushed into every submit payload
  let _activeTask = null;     // { init, pause, resume, abort } interface

  // ─── Public API ────────────────────────────────────────────────────────────

  const TaskCore = {
    /**
     * Called once per task page load.
     * Captures timezone offset + device info and POSTs to SESSION_META_URL.
     */
    init(sessionId, csrfToken) {
      _sessionId = sessionId;
      _csrfToken = csrfToken;
      _initPerfTime = performance.now();

      const timezoneOffsetMinutes = new Date().getTimezoneOffset();
      const deviceMeta = {
        user_agent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screen_width: screen.width,
        screen_height: screen.height,
      };

      fetch(window.SESSION_META_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          session_id: sessionId,
          timezone_offset_minutes: timezoneOffsetMinutes,
          device_meta: deviceMeta,
        }),
      }).catch(function () {
        // Non-critical — proceed even if the meta POST fails
      });

      _attachLifecycleListeners();
      _attachOfflineListeners();
    },

    /**
     * Validates mandatory envelope fields and POSTs the result payload to
     * TASK_SUBMIT_URL.  Returns a Promise.
     * Rejects immediately (no network request) if any required field is missing
     * or if the browser is offline.
     */
    submit(payload) {
      var REQUIRED = [
        "session_id",
        "task_type",
        "task_version",
        "started_at",
        "ended_at",
        "duration_ms",
        "input_modality",
        "trials",
        "summary",
      ];

      for (var i = 0; i < REQUIRED.length; i++) {
        var field = REQUIRED[i];
        if (!(field in payload)) {
          return Promise.reject(new Error("Missing required field: " + field));
        }
      }

      if (!navigator.onLine) {
        return Promise.reject(
          new Error("You are offline. Cannot submit task result.")
        );
      }

      var body = Object.assign({}, payload, {
        session_id: _sessionId,
        interruptions: _interruptions.slice(),
      });

      return fetch(window.TASK_SUBMIT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": _csrfToken,
        },
        body: JSON.stringify(body),
      }).then(function (response) {
        if (response.status === 422) {
          return response.json().then(function (data) {
            throw new Error(data.error || "Validation error (422)");
          });
        }
        return response.json();
      });
    },

    /**
     * Appends an event to the in-memory interruption log.
     * The log is included automatically in every submit() payload.
     */
    logEvent(type, detail) {
      _interruptions.push({
        type: type,
        detail: detail || null,
        at: TaskCore.wallClock(),
      });
    },

    /**
     * Returns milliseconds elapsed since TaskCore.init() was called,
     * using performance.now() for sub-millisecond accuracy.
     */
    now() {
      if (_initPerfTime === null) return 0;
      return performance.now() - _initPerfTime;
    },

    /**
     * Returns the current wall-clock time as an ISO-8601 UTC string.
     */
    wallClock() {
      return new Date().toISOString();
    },

    /**
     * Registers the active task's lifecycle interface.
     * Replaces any previously registered task.
     *
     * taskObject must implement: { init?, pause, resume, abort }
     */
    registerTask(taskObject) {
      _activeTask = taskObject;
    },
  };

  // ─── Private helpers ───────────────────────────────────────────────────────

  function _attachLifecycleListeners() {
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") {
        TaskCore.logEvent("visibility_hidden", { at: TaskCore.wallClock() });
        if (_activeTask && typeof _activeTask.pause === "function") {
          _activeTask.pause();
        }
      } else if (document.visibilityState === "visible") {
        TaskCore.logEvent("visibility_visible", { at: TaskCore.wallClock() });
        if (_activeTask && typeof _activeTask.resume === "function") {
          _activeTask.resume();
        }
      }
    });

    window.addEventListener("pagehide", function () {
      TaskCore.logEvent("pagehide", { at: TaskCore.wallClock() });
      if (_activeTask && typeof _activeTask.abort === "function") {
        _activeTask.abort("pagehide");
      }
    });

    window.addEventListener("beforeunload", function () {
      TaskCore.logEvent("beforeunload", { at: TaskCore.wallClock() });
      if (_activeTask && typeof _activeTask.abort === "function") {
        _activeTask.abort("beforeunload");
      }
    });
  }

  function _attachOfflineListeners() {
    window.addEventListener("offline", function () {
      TaskCore.logEvent("offline", { at: TaskCore.wallClock() });
      if (_activeTask && typeof _activeTask.abort === "function") {
        _activeTask.abort("offline");
      }

      // Non-blocking offline banner
      var banner = document.getElementById("task-core-offline-banner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "task-core-offline-banner";
        banner.style.cssText =
          "position:fixed;top:0;left:0;right:0;background:#e74c3c;color:#fff;" +
          "padding:0.75rem 1rem;z-index:9999;text-align:center;";
        banner.textContent =
          "You appear to be offline \u2014 your progress up to this point has been noted. " +
          "Reconnect to continue.";
        document.body.prepend(banner);
      }
    });

    window.addEventListener("online", function () {
      var banner = document.getElementById("task-core-offline-banner");
      if (banner) banner.remove();

      // Prompt user to restart the session
      if (window.Swal) {
        Swal.fire({
          title: "Back online",
          text: "You are back online. Please restart your session to continue.",
          icon: "info",
          confirmButtonText: "OK",
        });
      } else {
        // Fallback if SweetAlert2 is not yet loaded
        alert(
          "You are back online. Please restart your session to continue."
        );
      }
    });
  }

  // ─── Export ────────────────────────────────────────────────────────────────
  window.TaskCore = TaskCore;
})();

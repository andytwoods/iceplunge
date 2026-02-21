/**
 * pvt.js — Psychomotor Vigilance Task
 *
 * 60-second task. A red counter appears at random ISI (2–10 s, seeded).
 * The participant taps/clicks as fast as possible. RT recorded via TaskCore.now().
 * Lapses: RT > 500 ms. Anticipations: tap before stimulus appears (RT < 100 ms).
 * Auto-submits after durationMs.
 *
 * Requires window.TaskCore, window.TASK_SUBMIT_URL, window.TASK_TASK_URL,
 * window.TASK_COMPLETE_URL, and window.TASK_CONFIG already set.
 */
(function () {
  "use strict";

  var TASK_TYPE = "pvt";
  var TASK_VERSION = "1.0";
  var DURATION_MS = 60000;
  var ISI_MIN = 2000;
  var ISI_MAX = 10000;
  var LAPSE_THRESHOLD = 500;
  var ANTICIPATION_THRESHOLD = 100;
  var NO_RESPONSE_THRESHOLD = 2000;

  // ─── Seeded PRNG (Mulberry32) ──────────────────────────────────────────────
  function makeRng(seed) {
    var h = 0;
    for (var i = 0; i < seed.length; i++) {
      h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
    }
    // prefix seed so PVT and SART get different sequences from the same session seed
    h = (Math.imul(h, 1664525) + 1013904223) | 0;
    return function () {
      h += 0x6d2b79f5;
      var t = Math.imul(h ^ (h >>> 15), 1 | h);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function init(config) {
    var rng = makeRng((config.seed || "") + "_pvt");
    var durationMs = config.durationMs || DURATION_MS;
    var startedAt = TaskCore.wallClock();
    var taskStartMs = TaskCore.now();

    var trials = [];
    var stimulusStartMs = null;  // null = we are in the ISI period
    var isiTimer = null;
    var noResponseTimer = null;
    var animTimer = null;
    var taskEndTimer = null;
    var isPaused = false;
    var isRunning = false;
    var isStopped = false;

    var container = document.getElementById("task-container");
    container.style.cssText = "background:#000;min-height:300px;cursor:pointer;user-select:none;-webkit-user-select:none;";

    var displayEl = document.createElement("div");
    displayEl.style.cssText = (
      "position:relative;top:50%;transform:translateY(50%);" +
      "font-size:4rem;font-weight:bold;color:#e74c3c;text-align:center;" +
      "padding:2rem;letter-spacing:2px;"
    );
    container.appendChild(displayEl);

    function randomISI() {
      return ISI_MIN + rng() * (ISI_MAX - ISI_MIN);
    }

    function clearTimers() {
      clearTimeout(isiTimer);
      clearTimeout(noResponseTimer);
      cancelAnimationFrame(animTimer);
      clearTimeout(taskEndTimer);
    }

    function startISI() {
      if (!isRunning || isPaused) return;
      stimulusStartMs = null;
      displayEl.textContent = "";
      var isi = randomISI();
      isiTimer = setTimeout(showStimulus, isi);
    }

    function showStimulus() {
      if (!isRunning || isPaused) return;
      stimulusStartMs = TaskCore.now();

      // Animate counter
      function animate() {
        if (stimulusStartMs === null || !isRunning) return;
        var elapsed = Math.round(TaskCore.now() - stimulusStartMs);
        displayEl.textContent = elapsed;
        animTimer = requestAnimationFrame(animate);
      }
      animTimer = requestAnimationFrame(animate);

      // Auto-record non-response after NO_RESPONSE_THRESHOLD
      noResponseTimer = setTimeout(function () {
        if (stimulusStartMs !== null && isRunning) {
          recordResponse(false);
        }
      }, NO_RESPONSE_THRESHOLD);
    }

    function recordResponse(isUserTap) {
      var responseMs = TaskCore.now();

      if (stimulusStartMs === null) {
        // Tap during ISI = anticipation
        if (!isUserTap) return;
        clearTimeout(isiTimer);
        trials.push({
          stimulus_at_ms: null,
          response_at_ms: Math.round(responseMs),
          rt_ms: null,
          is_anticipation: true,
          is_lapse: false,
          responded: true,
        });
        startISI();
        return;
      }

      clearTimeout(noResponseTimer);
      cancelAnimationFrame(animTimer);

      var rtMs = Math.round(responseMs - stimulusStartMs);
      var isAnticipation = rtMs < ANTICIPATION_THRESHOLD;
      var isLapse = rtMs > LAPSE_THRESHOLD;

      trials.push({
        stimulus_at_ms: Math.round(stimulusStartMs),
        response_at_ms: Math.round(responseMs),
        rt_ms: isUserTap ? rtMs : null,
        is_anticipation: isAnticipation,
        is_lapse: isLapse || !isUserTap,
        responded: isUserTap,
      });

      stimulusStartMs = null;
      displayEl.textContent = "";

      if (isRunning) startISI();
    }

    function handleInteraction(e) {
      e.preventDefault();
      if (!isRunning || isPaused || isStopped) return;
      recordResponse(true);
    }

    function endTask() {
      if (isStopped) return;
      isStopped = true;
      isRunning = false;
      clearTimers();
      container.removeEventListener("click", handleInteraction);
      container.removeEventListener("touchend", handleInteraction);

      displayEl.style.color = "#fff";
      displayEl.textContent = "Submitting\u2026";

      var endedAt = TaskCore.wallClock();
      TaskCore.submit({
        task_type: TASK_TYPE,
        task_version: TASK_VERSION,
        started_at: startedAt,
        ended_at: endedAt,
        duration_ms: durationMs,
        input_modality: "touch",
        trials: trials,
        summary: {},
      }).then(function (data) {
        if (data.next_task) {
          window.location.href = window.TASK_TASK_URL;
        } else {
          window.location.href = window.TASK_COMPLETE_URL;
        }
      }).catch(function (err) {
        displayEl.textContent = "Error: " + err.message;
      });
    }

    // Start running
    isRunning = true;
    container.addEventListener("click", handleInteraction);
    container.addEventListener("touchend", handleInteraction);
    startISI();
    taskEndTimer = setTimeout(endTask, durationMs);

    TaskCore.registerTask({
      pause: function () {
        isPaused = true;
        clearTimeout(isiTimer);
        clearTimeout(noResponseTimer);
        cancelAnimationFrame(animTimer);
      },
      resume: function () {
        isPaused = false;
        startISI();
      },
      abort: function (reason) {
        isStopped = true;
        isRunning = false;
        clearTimers();
      },
    });
  }

  window.PvtTask = { init: init };
})();

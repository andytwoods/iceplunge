/**
 * sart.js — Sustained Attention to Response Task
 *
 * Digits 1–9 appear in rapid succession (250 ms stimulus, 900 ms ISI).
 * Participant taps for every digit EXCEPT 3 (no-go target, ~11% of trials).
 * Runs for durationMs (default 75 000 ms). Auto-submits on completion.
 *
 * Requires window.TaskCore, window.TASK_SUBMIT_URL, window.TASK_TASK_URL,
 * window.TASK_COMPLETE_URL, and window.TASK_CONFIG.
 */
(function () {
  "use strict";

  var TASK_TYPE = "sart";
  var TASK_VERSION = "1.0";
  var DURATION_MS = 75000;
  var STIMULUS_MS = 250;
  var ISI_MS = 900;
  var NOGO_DIGIT = 3;

  function makeRng(seed) {
    var h = 0;
    for (var i = 0; i < seed.length; i++) {
      h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
    }
    h = (Math.imul(h, 22695477) + 1) | 0;
    return function () {
      h += 0x6d2b79f5;
      var t = Math.imul(h ^ (h >>> 15), 1 | h);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Generate a digit sequence (~11% no-go)
  function buildSequence(rng, durationMs) {
    var trialDuration = STIMULUS_MS + ISI_MS; // 1150 ms per trial
    var count = Math.ceil(durationMs / trialDuration) + 5; // a few extra
    var seq = [];
    var digits = [1, 2, 3, 4, 5, 6, 7, 8, 9];
    for (var i = 0; i < count; i++) {
      // ~11% chance of no-go (digit 3)
      if (rng() < 0.111) {
        seq.push(NOGO_DIGIT);
      } else {
        // Pick a random go digit (1-9 excluding 3)
        var goDigits = digits.filter(function (d) { return d !== NOGO_DIGIT; });
        seq.push(goDigits[Math.floor(rng() * goDigits.length)]);
      }
    }
    return seq;
  }

  function init(config) {
    var rng = makeRng((config.seed || "") + "_sart");
    var durationMs = config.durationMs || DURATION_MS;
    var startedAt = TaskCore.wallClock();

    var sequence = buildSequence(rng, durationMs);
    var seqIndex = 0;
    var trials = [];
    var isRunning = false;
    var isPaused = false;
    var isStopped = false;
    var taskEndTimer = null;
    var trialTimer = null;
    var currentTrialStart = null;
    var currentDigit = null;
    var responded = false;

    var container = document.getElementById("task-container");
    container.style.cssText = "background:#111;min-height:300px;cursor:pointer;user-select:none;-webkit-user-select:none;";

    var digitEl = document.createElement("div");
    digitEl.style.cssText = (
      "font-size:6rem;font-weight:bold;color:#fff;text-align:center;" +
      "padding-top:60px;min-height:200px;line-height:1;"
    );
    container.appendChild(digitEl);

    var instrEl = document.createElement("p");
    instrEl.style.cssText = "color:#aaa;text-align:center;font-size:0.9rem;margin-top:1rem;";
    instrEl.textContent = "Tap for every digit except 3";
    container.appendChild(instrEl);

    function showNextTrial() {
      if (!isRunning || isPaused || seqIndex >= sequence.length) {
        endTask();
        return;
      }
      currentDigit = sequence[seqIndex++];
      currentTrialStart = TaskCore.now();
      responded = false;
      digitEl.textContent = currentDigit;

      // Hide stimulus after STIMULUS_MS
      trialTimer = setTimeout(function () {
        digitEl.textContent = "";
        // Response window extends through ISI
        trialTimer = setTimeout(function () {
          // Record non-response if no tap
          if (!responded) {
            var isNogo = currentDigit === NOGO_DIGIT;
            trials.push({
              digit: currentDigit,
              is_nogo: isNogo,
              responded: false,
              rt_ms: null,
              is_commission: false,
              is_omission: !isNogo,
            });
          }
          showNextTrial();
        }, ISI_MS - STIMULUS_MS);
      }, STIMULUS_MS);
    }

    function handleInteraction(e) {
      e.preventDefault();
      if (!isRunning || isPaused || isStopped || responded) return;
      var rtMs = Math.round(TaskCore.now() - currentTrialStart);
      var isNogo = currentDigit === NOGO_DIGIT;
      responded = true;
      trials.push({
        digit: currentDigit,
        is_nogo: isNogo,
        responded: true,
        rt_ms: rtMs,
        is_commission: isNogo,
        is_omission: false,
      });
    }

    function endTask() {
      if (isStopped) return;
      isStopped = true;
      isRunning = false;
      clearTimeout(trialTimer);
      clearTimeout(taskEndTimer);
      container.removeEventListener("click", handleInteraction);
      container.removeEventListener("touchend", handleInteraction);

      digitEl.textContent = "Submitting\u2026";

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
        window.location.href = data.next_task ? window.TASK_TASK_URL : window.TASK_COMPLETE_URL;
      }).catch(function (err) {
        digitEl.textContent = "Error: " + err.message;
      });
    }

    isRunning = true;
    container.addEventListener("click", handleInteraction);
    container.addEventListener("touchend", handleInteraction);
    showNextTrial();
    taskEndTimer = setTimeout(endTask, durationMs);

    TaskCore.registerTask({
      pause: function () {
        isPaused = true;
        clearTimeout(trialTimer);
        digitEl.textContent = "";
      },
      resume: function () {
        isPaused = false;
        showNextTrial();
      },
      abort: function () {
        isStopped = true;
        isRunning = false;
        clearTimeout(trialTimer);
        clearTimeout(taskEndTimer);
      },
    });
  }

  window.SartTask = { init: init };
})();

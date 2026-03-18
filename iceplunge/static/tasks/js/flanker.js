/**
 * flanker.js — Eriksen Flanker Task
 *
 * Rows of 5 arrows: congruent (all same direction) or incongruent (centre differs).
 * ~50/50 ratio, seeded. Participant presses Left or Right for the centre arrow.
 * 500 ms response window, 500 ms blank ISI. Runs for durationMs (default 75 000 ms).
 *
 * Requires window.TaskCore, window.TASK_SUBMIT_URL, window.TASK_TASK_URL,
 * window.TASK_COMPLETE_URL, and window.TASK_CONFIG.
 */
(function () {
  "use strict";

  var TASK_TYPE = "flanker";
  var TASK_VERSION = "1.0";
  var DURATION_MS = 75000;
  var RESPONSE_WINDOW_MS = 500;
  var ISI_MS = 500;

  function makeRng(seed) {
    var h = 0;
    for (var i = 0; i < seed.length; i++) {
      h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
    }
    h = (Math.imul(h, 1664525) + 1013904223) | 0;
    return function () {
      h += 0x6d2b79f5;
      var t = Math.imul(h ^ (h >>> 15), 1 | h);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function buildTrial(rng) {
    var isCongruent = rng() < 0.5;
    var direction = rng() < 0.5 ? "left" : "right";
    var arrows;
    if (isCongruent) {
      arrows = direction === "left" ? "< < < < <" : "> > > > >";
    } else {
      arrows = direction === "left" ? "> > < > >" : "< < > < <";
    }
    return { arrows: arrows, direction: direction, is_congruent: isCongruent };
  }

  function init(config) {
    var rng = makeRng((config.seed || "") + "_flanker");
    var durationMs = config.durationMs || DURATION_MS;
    var startedAt = TaskCore.wallClock();

    var trials = [];
    var isRunning = false;
    var isPaused = false;
    var isStopped = false;
    var trialTimer = null;
    var taskEndTimer = null;
    var currentTrial = null;
    var currentTrialStart = null;
    var responded = false;

    var container = document.getElementById("task-container");
    container.className = "task-stimulus-area";
    container.style.cssText = "min-height:300px;user-select:none;-webkit-user-select:none;";

    var stimulusEl = document.createElement("div");
    stimulusEl.className = "task-stimulus-text";
    stimulusEl.style.cssText = (
      "font-size:3rem;letter-spacing:0.3rem;text-align:center;" +
      "padding:60px 0;min-height:180px;line-height:1;"
    );
    container.appendChild(stimulusEl);

    var btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:1rem;justify-content:center;padding:1rem;";

    var leftBtn = makeBtn("\u2190 Left");
    var rightBtn = makeBtn("Right \u2192");
    btnRow.appendChild(leftBtn);
    btnRow.appendChild(rightBtn);
    container.appendChild(btnRow);

    function makeBtn(label) {
      var btn = document.createElement("button");
      btn.textContent = label;
      btn.className = "flanker-btn";
      btn.style.cssText = "padding:1rem 2rem;font-size:1.2rem;border:2px solid;border-radius:6px;cursor:pointer;";
      return btn;
    }

    leftBtn.addEventListener("click", function () { handleResponse("left"); });
    rightBtn.addEventListener("click", function () { handleResponse("right"); });

    // Keyboard support (registered in startTask, not here)
    var keyHandler = function (e) {
      if (e.key === "ArrowLeft" || e.key === "z" || e.key === "Z") handleResponse("left");
      if (e.key === "ArrowRight" || e.key === "/") handleResponse("right");
    };

    var startOverlayEl = document.createElement("div");
    startOverlayEl.className = "task-start-overlay";
    startOverlayEl.style.cssText = (
      "position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);" +
      "font-size:1.25rem;padding:1rem;"
    );
    startOverlayEl.textContent = "Click or press Space to start";
    container.style.position = "relative";
    container.appendChild(startOverlayEl);

    function showNextTrial() {
      if (!isRunning || isPaused || isStopped) return;
      currentTrial = buildTrial(rng);
      currentTrialStart = TaskCore.now();
      responded = false;
      stimulusEl.textContent = currentTrial.arrows;

      trialTimer = setTimeout(function () {
        stimulusEl.textContent = "";
        if (!responded) {
          trials.push({
            arrows: currentTrial.arrows,
            direction: currentTrial.direction,
            is_congruent: currentTrial.is_congruent,
            responded: false,
            response: null,
            correct: false,
            rt_ms: null,
          });
        }
        trialTimer = setTimeout(showNextTrial, ISI_MS);
      }, RESPONSE_WINDOW_MS);
    }

    function flashBtn(btn) {
      btn.style.background = "#3273dc";
      btn.style.borderColor = "#3273dc";
      btn.style.color = "#fff";
      setTimeout(function () {
        btn.style.background = "";
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 150);
    }

    function handleResponse(direction) {
      if (!isRunning || isPaused || isStopped || responded || currentTrial === null) return;
      responded = true;
      flashBtn(direction === "left" ? leftBtn : rightBtn);
      var rtMs = Math.round(TaskCore.now() - currentTrialStart);
      trials.push({
        arrows: currentTrial.arrows,
        direction: currentTrial.direction,
        is_congruent: currentTrial.is_congruent,
        responded: true,
        response: direction,
        correct: direction === currentTrial.direction,
        rt_ms: rtMs,
      });
    }

    function endTask() {
      if (isStopped) return;
      isStopped = true;
      isRunning = false;
      clearTimeout(trialTimer);
      clearTimeout(taskEndTimer);
      document.removeEventListener("keydown", keyHandler);

      stimulusEl.textContent = "Submitting\u2026";

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
        TaskCore.navigateAfterTask(data.next_task);
      }).catch(function (err) {
        stimulusEl.textContent = "Error: " + err.message;
      });
    }

    function startTask() {
      startOverlayEl.style.display = "none";
      document.addEventListener("keydown", keyHandler);
      isRunning = true;
      showNextTrial();
      taskEndTimer = setTimeout(endTask, durationMs);
    }

    function handleSpaceKey(e) {
      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        document.removeEventListener("keydown", handleSpaceKey);
        container.removeEventListener("click", handleStartClick);
        startTask();
      }
    }

    function handleStartClick() {
      document.removeEventListener("keydown", handleSpaceKey);
      container.removeEventListener("click", handleStartClick);
      startTask();
    }

    container.addEventListener("click", handleStartClick);
    document.addEventListener("keydown", handleSpaceKey);

    TaskCore.registerTask({
      pause: function () {
        isPaused = true;
        clearTimeout(trialTimer);
        stimulusEl.textContent = "";
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
        document.removeEventListener("keydown", keyHandler);
      },
    });
  }

  window.FlankerTask = { init: init };
})();

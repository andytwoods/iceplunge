/**
 * digit_symbol.js — Digit Symbol Coding Task
 *
 * A fixed key maps digits 1–9 to unique symbols (shown at top).
 * One digit is shown at a time; participant selects from 4 options (one correct, 3 distractors).
 * Symbol mapping and digit order are seeded from config.seed.
 * Runs for durationMs (default 75 000 ms). Auto-submits on completion.
 *
 * Requires window.TaskCore, window.TASK_SUBMIT_URL, window.TASK_TASK_URL,
 * window.TASK_COMPLETE_URL, and window.TASK_CONFIG.
 */
(function () {
  "use strict";

  var TASK_TYPE = "digit_symbol";
  var TASK_VERSION = "1.0";
  var DURATION_MS = 75000;

  // 9 symbols (Unicode geometric shapes) used as substitutes for digits 1–9
  var SYMBOL_POOL = ["\u25CF", "\u25B2", "\u25BC", "\u25C6", "\u2605", "\u25A0", "\u2764", "\u2660", "\u2663"];

  function makeRng(seed) {
    var h = 0;
    for (var i = 0; i < seed.length; i++) {
      h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
    }
    h = (Math.imul(h, 69069) + 1) | 0;
    return function () {
      h += 0x6d2b79f5;
      var t = Math.imul(h ^ (h >>> 15), 1 | h);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffle(arr, rng) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function init(config) {
    var rng = makeRng((config.seed || "") + "_ds");
    var durationMs = config.durationMs || DURATION_MS;
    var startedAt = null;

    // Build per-session symbol mapping (digit 1–9 → symbol)
    var symbolMap = {};  // digit → symbol
    var shuffledSymbols = shuffle(SYMBOL_POOL, rng);
    for (var d = 1; d <= 9; d++) {
      symbolMap[d] = shuffledSymbols[d - 1];
    }

    var trials = [];
    var isRunning = false;
    var isPaused = false;
    var isStopped = false;
    var taskEndTimer = null;

    var container = document.getElementById("task-container");
    container.innerHTML = "";
    container.style.cssText = "padding:1rem;";

    // --- Key display (always visible, even before start) ---
    var keyTable = document.createElement("div");
    keyTable.style.cssText = "display:flex;gap:0.5rem;margin-bottom:1.5rem;justify-content:center;flex-wrap:wrap;";
    for (var digit = 1; digit <= 9; digit++) {
      var cell = document.createElement("div");
      cell.className = "digit-symbol-key-cell";
      cell.style.cssText = "border:1px solid;border-radius:4px;padding:0.25rem 0.5rem;text-align:center;min-width:3rem;";
      cell.innerHTML = "<div class='digit-symbol-key-digit' style='font-size:1rem;'>" + digit + "</div>" +
                       "<div style='font-size:1.5rem;'>" + symbolMap[digit] + "</div>";
      keyTable.appendChild(cell);
    }
    container.appendChild(keyTable);

    // --- Start prompt (shown in place of stimulus until user starts) ---
    var startPromptEl = document.createElement("div");
    startPromptEl.className = "task-start-overlay";
    startPromptEl.style.cssText = "font-size:1.25rem;text-align:center;padding:2rem 1rem;";
    startPromptEl.textContent = "Study the key above, then click or press Space to start";
    container.appendChild(startPromptEl);

    // --- Current stimulus (built now, appended on start) ---
    var stimulusEl = document.createElement("div");
    stimulusEl.style.cssText = "font-size:4rem;text-align:center;margin:1rem 0;min-height:80px;";

    // --- Option buttons (built now, appended on start) ---
    var optionRow = document.createElement("div");
    optionRow.style.cssText = "display:flex;gap:0.75rem;justify-content:center;flex-wrap:wrap;";

    function showNextTrial() {
      if (!isRunning || isPaused || isStopped) return;
      var targetDigit = Math.floor(rng() * 9) + 1;
      var targetSymbol = symbolMap[targetDigit];
      stimulusEl.textContent = targetDigit;

      // Build 4 options: 1 correct, 3 distractors
      var distractorDigits = Object.keys(symbolMap)
        .map(Number)
        .filter(function (d) { return d !== targetDigit; });
      // Shuffle and take 3
      var shuffled = shuffle(distractorDigits, rng).slice(0, 3);
      var options = shuffle([targetDigit].concat(shuffled), rng);

      optionRow.innerHTML = "";
      var trialStartMs = TaskCore.now();

      options.forEach(function (optDigit) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = symbolMap[optDigit];
        btn.className = "digit-symbol-option-btn";
        btn.style.cssText = "font-size:2rem;padding:0.75rem 1.5rem;border:2px solid;border-radius:8px;cursor:pointer;min-width:4rem;";
        btn.addEventListener("click", function () {
          if (!isRunning || isPaused || isStopped) return;
          var rtMs = Math.round(TaskCore.now() - trialStartMs);
          var correct = optDigit === targetDigit;
          trials.push({
            digit: targetDigit,
            target_symbol: targetSymbol,
            selected_symbol: symbolMap[optDigit],
            stimulus_at_ms: Math.round(trialStartMs),
            response_at_ms: Math.round(TaskCore.now()),
            rt_ms: rtMs,
            correct: correct,
            responded: true,
          });
          showNextTrial();
        });
        optionRow.appendChild(btn);
      });
    }

    function endTask() {
      if (isStopped) return;
      isStopped = true;
      isRunning = false;
      clearTimeout(taskEndTimer);

      stimulusEl.textContent = "Submitting\u2026";
      optionRow.innerHTML = "";

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
      startedAt = TaskCore.wallClock();
      container.removeChild(startPromptEl);
      container.appendChild(stimulusEl);
      container.appendChild(optionRow);
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
      },
      resume: function () {
        isPaused = false;
        showNextTrial();
      },
      abort: function () {
        isStopped = true;
        isRunning = false;
        clearTimeout(taskEndTimer);
      },
    });
  }

  window.DigitSymbolTask = { init: init };
})();

/**
 * mood.js — Mood Rating Task
 *
 * Four 5-point scales: valence, arousal, stress, sharpness.
 * Submit button is enabled only after all four have a value.
 * Records started_at and ended_at.
 *
 * Requires window.TaskCore, window.TASK_SUBMIT_URL, window.TASK_TASK_URL,
 * window.TASK_COMPLETE_URL, and window.TASK_CONFIG.
 */
(function () {
  "use strict";

  var TASK_TYPE = "mood";
  var TASK_VERSION = "1.0";

  var SCALES = [
    { key: "valence",   label: "Mood", low: "Very negative", high: "Very positive" },
    { key: "arousal",   label: "Energy", low: "Very low", high: "Very high" },
    { key: "stress",    label: "Stress", low: "Not at all", high: "Extremely stressed" },
    { key: "sharpness", label: "Mental clarity", low: "Very foggy", high: "Very sharp" },
  ];

  function init(config) {
    var startedAt = TaskCore.wallClock();
    var ratings = {};

    var container = document.getElementById("task-container");
    container.innerHTML = "";
    container.style.cssText = "max-width:600px;margin:0 auto;padding:1rem;";

    var form = document.createElement("div");

    SCALES.forEach(function (scale) {
      var section = document.createElement("div");
      section.style.cssText = "margin-bottom:2rem;";

      var label = document.createElement("p");
      label.style.cssText = "font-weight:bold;font-size:1.1rem;margin-bottom:0.5rem;";
      label.textContent = scale.label;
      section.appendChild(label);

      var anchors = document.createElement("div");
      anchors.style.cssText = "display:flex;justify-content:space-between;font-size:0.8rem;color:#888;margin-bottom:0.25rem;";
      anchors.innerHTML = "<span>" + scale.low + "</span><span>" + scale.high + "</span>";
      section.appendChild(anchors);

      var btnRow = document.createElement("div");
      btnRow.style.cssText = "display:flex;gap:0.5rem;";

      for (var v = 1; v <= 5; v++) {
        (function (val) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.textContent = val;
          btn.dataset.key = scale.key;
          btn.dataset.val = val;
          btn.style.cssText = (
            "flex:1;padding:0.75rem 0;border:2px solid #ccc;" +
            "border-radius:6px;background:#fff;font-size:1.1rem;cursor:pointer;"
          );
          btn.addEventListener("click", function () {
            // Deselect siblings
            btnRow.querySelectorAll("button").forEach(function (b) {
              b.style.background = "#fff";
              b.style.borderColor = "#ccc";
              b.style.color = "#000";
            });
            btn.style.background = "#3273dc";
            btn.style.borderColor = "#3273dc";
            btn.style.color = "#fff";
            ratings[scale.key] = val;
            updateSubmit();
          });
          btnRow.appendChild(btn);
        })(v);
      }

      section.appendChild(btnRow);
      form.appendChild(section);
    });

    container.appendChild(form);

    var submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.textContent = "Submit";
    submitBtn.disabled = true;
    submitBtn.style.cssText = (
      "width:100%;padding:1rem;background:#48c774;color:#fff;" +
      "border:none;border-radius:6px;font-size:1.1rem;cursor:pointer;margin-top:1rem;"
    );
    submitBtn.addEventListener("click", function () {
      if (submitBtn.disabled) return;
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting\u2026";

      var endedAt = TaskCore.wallClock();
      TaskCore.submit({
        task_type: TASK_TYPE,
        task_version: TASK_VERSION,
        started_at: startedAt,
        ended_at: endedAt,
        duration_ms: Date.now() - new Date(startedAt).getTime(),
        input_modality: "touch",
        trials: [Object.assign({}, ratings)],
        summary: Object.assign({}, ratings),
      }).then(function (data) {
        window.location.href = data.next_task ? window.TASK_TASK_URL : window.TASK_COMPLETE_URL;
      }).catch(function (err) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit";
        alert("Error: " + err.message);
      });
    });
    container.appendChild(submitBtn);

    function updateSubmit() {
      var allRated = SCALES.every(function (s) { return ratings[s.key] !== undefined; });
      submitBtn.disabled = !allRated;
    }

    TaskCore.registerTask({
      pause: function () {},
      resume: function () {},
      abort: function () {},
    });
  }

  window.MoodTask = { init: init };
})();

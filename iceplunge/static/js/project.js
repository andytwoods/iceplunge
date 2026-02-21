/* Project specific Javascript goes here. */

/* ── HTMX CONFIGURATION ─────────────────────────────────────────────────────── */
// Allow HTMX to swap content on 422 (form validation errors) in addition to 2xx.
// Must be set before any HTMX processing occurs; safe here because project.js
// is deferred and loads after htmx.min.js.
htmx.config.responseHandling = [
  {code: "204", swap: false},
  {code: "[23]..", swap: true},
  {code: "422", swap: true},
  {code: "[45]..", swap: false, error: true},
  {code: "...", swap: true},
];

/* ── PLUNGE MODAL ───────────────────────────────────────────────────────────── */
function openPlungeModal() {
  document.getElementById('plunge-modal').classList.add('is-active');
}

function closePlungeModal() {
  document.getElementById('plunge-modal').classList.remove('is-active');
}

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closePlungeModal();
});

/* ── MORE INFO DETAILS PERSISTENCE ─────────────────────────────────────────── */
var MORE_INFO_KEY = 'moreInfoOpen';

document.addEventListener('toggle', function (e) {
  if (e.target && e.target.id === 'more-info-details') {
    localStorage.setItem(MORE_INFO_KEY, e.target.open ? '1' : '0');
  }
}, true);

document.body.addEventListener('htmx:afterSwap', function (e) {
  if (e.target.id === 'log-plunge-box-body') {
    var details = document.getElementById('more-info-details');
    if (details && localStorage.getItem(MORE_INFO_KEY) === '1') {
      details.open = true;
    }
  }
});

/* ── HTMX EVENT LISTENERS ───────────────────────────────────────────────────── */
document.addEventListener('plungeLogged', function (e) {
  window.showToast(e.detail.message, e.detail.type);
  closePlungeModal();
  var emptyState = document.getElementById('empty-plunge-state');
  if (emptyState) emptyState.remove();
});

/* ── TOAST NOTIFICATION SYSTEM ────────────────────────────────────────────── */
(function () {
  'use strict';

  var AUTO_DISMISS_MS = 5000;

  function dismissToast(el) {
    if (el.classList.contains('is-hiding')) return;
    el.classList.add('is-hiding');
    setTimeout(function () { el.remove(); }, 400);
  }

  function armToast(el) {
    // Delete button
    var btn = el.querySelector('.delete');
    if (btn) btn.addEventListener('click', function () { dismissToast(el); });
    // Auto-dismiss
    setTimeout(function () { dismissToast(el); }, AUTO_DISMISS_MS);
  }

  // Expose for programmatic use elsewhere in the project
  window.showToast = function (message, type) {
    var container = document.getElementById('toastContainer');
    if (!container) return;
    var el = document.createElement('div');
    el.className = 'notification ' + (type ? 'is-' + type : 'is-info');
    el.innerHTML = '<button class="delete"></button>' + message;
    container.appendChild(el);
    armToast(el);
  };

  document.addEventListener('DOMContentLoaded', function () {
    var container = document.getElementById('toastContainer');
    if (!container) return;
    container.querySelectorAll('.notification').forEach(armToast);
  });
}());

/* ── DESELECTABLE RADIO BUTTONS ────────────────────────────────────────────── */
(function () {
  'use strict';

  // Resolve the radio input from whatever element was actually clicked
  // (handles direct clicks on <input> and clicks on <label> or children of <label>).
  function radioForTarget(target) {
    if (target.type === 'radio') return target;
    var label = target.closest('label');
    if (label && label.htmlFor) return document.getElementById(label.htmlFor);
    return null;
  }

  // Record pre-click checked state on mousedown (before browser changes anything).
  document.addEventListener('mousedown', function (e) {
    var radio = radioForTarget(e.target);
    if (radio) radio.dataset.wasChecked = radio.checked ? 'true' : 'false';
  });

  // On click, if the radio was already checked, uncheck it instead.
  // preventDefault stops the label from re-activating the radio after we uncheck it.
  document.addEventListener('click', function (e) {
    var radio = radioForTarget(e.target);
    if (!radio) return;
    if (radio.dataset.wasChecked === 'true') {
      e.preventDefault();
      radio.checked = false;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
    }
    delete radio.dataset.wasChecked;
  });
}());

/* ── MORE INFO FORM HELPERS ────────────────────────────────────────────────── */
window.clearMoreInfo = function (formEl) {
  formEl.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(function (el) {
    el.checked = false;
  });
  formEl.querySelectorAll('input[type="number"], input[type="text"]').forEach(function (el) {
    el.value = '';
  });
};

/* ── ACCESSIBILITY WIDGET ──────────────────────────────────────────────────── */
(function () {
  'use strict';

  const DEFAULTS = { contrast: 'standard', text: 'standard', motion: 'standard' };
  const LS_KEY = 'a11yPrefs';
  const html = document.documentElement;

  function loadPrefs() {
    try {
      return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem(LS_KEY) || '{}'));
    } catch (_) {
      return Object.assign({}, DEFAULTS);
    }
  }

  function savePrefs(prefs) {
    try { localStorage.setItem(LS_KEY, JSON.stringify(prefs)); } catch (_) {}
  }

  function applyPrefs(prefs) {
    if (prefs.contrast === 'standard') {
      html.removeAttribute('data-a11y-contrast');
    } else {
      html.setAttribute('data-a11y-contrast', prefs.contrast);
    }
    if (prefs.text === 'standard') {
      html.removeAttribute('data-a11y-text');
    } else {
      html.setAttribute('data-a11y-text', prefs.text);
    }
    if (prefs.motion === 'standard') {
      html.removeAttribute('data-a11y-motion');
    } else {
      html.setAttribute('data-a11y-motion', prefs.motion);
    }
  }

  function reflectPrefs(prefs) {
    ['contrast', 'text', 'motion'].forEach(function (key) {
      const radio = document.querySelector(
        'input[name="a11y-' + key + '"][value="' + prefs[key] + '"]'
      );
      if (radio) radio.checked = true;
    });
  }

  // Apply stored prefs immediately (before DOM ready) so there's no flash
  applyPrefs(loadPrefs());

  document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('a11yPanel');
    const close = document.getElementById('a11yClose');
    const reset = document.getElementById('a11yReset');

    if (!panel) return;

    let prefs = loadPrefs();
    let lastTrigger = null;

    reflectPrefs(prefs);

    function openPanel(triggerEl) {
      lastTrigger = triggerEl || null;
      panel.classList.add('is-open');
      if (close) close.focus();
    }

    function closePanel() {
      panel.classList.remove('is-open');
      if (lastTrigger) lastTrigger.focus();
    }

    // Wire all triggers (navbar + footer)
    document.querySelectorAll('.a11y-open-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        panel.classList.contains('is-open') ? closePanel() : openPanel(btn);
      });
    });

    if (close) close.addEventListener('click', closePanel);

    if (reset) {
      reset.addEventListener('click', function () {
        prefs = Object.assign({}, DEFAULTS);
        savePrefs(prefs);
        applyPrefs(prefs);
        reflectPrefs(prefs);
      });
    }

    ['contrast', 'text', 'motion'].forEach(function (key) {
      document.querySelectorAll('input[name="a11y-' + key + '"]').forEach(function (radio) {
        radio.addEventListener('change', function () {
          prefs[key] = radio.value;
          savePrefs(prefs);
          applyPrefs(prefs);
        });
      });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.classList.contains('is-open')) closePanel();
    });

    document.addEventListener('click', function (e) {
      if (!panel.classList.contains('is-open')) return;
      const clickedTrigger = e.target.closest('.a11y-open-btn');
      if (!clickedTrigger && !panel.contains(e.target)) closePanel();
    });
  });
}());

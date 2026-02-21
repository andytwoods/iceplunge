/* Project specific Javascript goes here. */

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
  // Record whether a radio was already checked before the click lands
  document.addEventListener('mousedown', function (e) {
    if (e.target.type === 'radio') {
      e.target.dataset.wasChecked = e.target.checked ? 'true' : 'false';
    }
  });
  // If it was already checked, uncheck it and fire change so any show/hide logic runs
  document.addEventListener('click', function (e) {
    if (e.target.type === 'radio' && e.target.dataset.wasChecked === 'true') {
      e.target.checked = false;
      delete e.target.dataset.wasChecked;
      e.target.dispatchEvent(new Event('change', { bubbles: true }));
    }
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

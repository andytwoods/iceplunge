# Manual Checks — iceplunge.tasks

These items require human verification in a browser before each release.

## T4.2 — task_core.js lifecycle events

- [ ] Open a task page and switch to another browser tab (or press Home on mobile).
  Switching back and checking the interruption log (via DevTools `TaskCore` object) should
  show a `visibility_hidden` entry followed by `visibility_visible`.

- [ ] Backgrounding the browser tab during a task should log a `visibility_hidden`
  interruption event and call the active task's `pause()` method.

- [ ] Closing the tab or navigating away mid-task should call the active task's `abort()`.

## T4.2 — Offline detection

- [ ] Simulate going offline (DevTools → Network → Offline) while on a task page.
  A red "You appear to be offline" banner should appear at the top of the page.

- [ ] Restoring connectivity should remove the banner and show a SweetAlert2 dialog
  prompting the user to restart their session.

- [ ] Attempting to call `TaskCore.submit()` while offline (via DevTools console) should
  reject the Promise immediately with a descriptive error, without making a network request.

## T5.1 — PVT task

- [ ] After 60 s the task calls `TaskCore.submit` automatically without manual interaction.
- [ ] A paused task (by backgrounding) does not record the pause duration as response time.
- [ ] Tapping before the red timer appears is counted as an anticipation and does not
  record a valid RT.

## T5.2 — SART task

- [ ] No-go digit (3) appears with approximately 11% frequency across a run.
- [ ] Tapping digit 3 is counted as a commission error.
- [ ] Failing to tap a go digit is counted as an omission error.

## T5.3 — Mood task

- [ ] Submit button is always enabled; clicking it before all four scales are rated shows
  a SweetAlert2 toast ("Please answer all questions before submitting.") and does not submit.
- [ ] After all four scales are rated, clicking Submit proceeds to submission normally.
- [ ] Selecting a value highlights it clearly; changing selection deselects the previous.
- [ ] All four scales show 7 buttons (1–7) with correct published anchor labels:
  - Mood: "Very bad" (1) — "Very good" (7)
  - Energy: "Calm / low energy" (1) — "Energetic / excited" (7)
  - Stress: "Not at all stressed" (1) — "Extremely stressed" (7)
  - Mental clarity: "Mentally foggy" (1) — "Mentally sharp" (7)

## T5.4 — Flanker task

- [ ] Congruent and incongruent trials appear in approximately 50/50 ratio.
- [ ] Arrow key (← / →) input and on-screen button input both register responses.

## T5.5 — Digit Symbol task

- [ ] Symbol mapping is consistent within a session but differs across sessions
  (due to per-session seeding).
- [ ] Symbols are randomised per-session and not hardcoded to a fixed mapping.

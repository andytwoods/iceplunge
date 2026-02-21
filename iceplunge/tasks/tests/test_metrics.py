"""Unit tests for server-side task metric computation functions."""
import pytest

from iceplunge.tasks.helpers.metrics.digit_symbol import compute_digit_symbol_summary
from iceplunge.tasks.helpers.metrics.flanker import compute_flanker_summary
from iceplunge.tasks.helpers.metrics.mood import compute_mood_summary
from iceplunge.tasks.helpers.metrics.pvt import compute_pvt_summary
from iceplunge.tasks.helpers.metrics.sart import compute_sart_summary


# ─────────────────────────────────────────────────────────────────────────────
# PVT
# ─────────────────────────────────────────────────────────────────────────────

class TestComputePvtSummary:
    def _trial(self, rt_ms, responded=True, is_anticipation=False, is_lapse=None):
        if is_lapse is None:
            is_lapse = rt_ms is not None and rt_ms > 500
        return {
            "rt_ms": rt_ms,
            "responded": responded,
            "is_anticipation": is_anticipation,
            "is_lapse": is_lapse,
        }

    def test_empty_trials_returns_none_metrics(self):
        result = compute_pvt_summary([])
        assert result["median_rt"] is None
        assert result["mean_rt"] is None
        assert result["valid_trial_count"] == 0

    def test_basic_median_and_mean(self):
        trials = [
            self._trial(200),
            self._trial(300),
            self._trial(400),
        ]
        result = compute_pvt_summary(trials)
        assert result["median_rt"] == 300
        assert result["mean_rt"] == pytest.approx(300.0)
        assert result["valid_trial_count"] == 3

    def test_lapse_count_above_500ms(self):
        trials = [self._trial(200), self._trial(600), self._trial(800)]
        result = compute_pvt_summary(trials)
        assert result["lapse_count"] == 2

    def test_anticipation_count_below_100ms(self):
        trials = [
            self._trial(50, is_anticipation=True),
            self._trial(300),
        ]
        result = compute_pvt_summary(trials)
        assert result["anticipation_count"] == 1
        # Anticipations excluded from valid_rts
        assert result["valid_trial_count"] == 1

    def test_rt_sd_single_trial(self):
        trials = [self._trial(300)]
        result = compute_pvt_summary(trials)
        assert result["rt_sd"] == 0.0

    def test_rt_sd_multiple_trials(self):
        trials = [self._trial(200), self._trial(400)]
        result = compute_pvt_summary(trials)
        assert result["rt_sd"] > 0

    def test_no_plunge_returns_empty(self):
        result = compute_pvt_summary([])
        assert result["lapse_count"] == 0
        assert result["anticipation_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# SART
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeSartSummary:
    def _go(self, rt_ms=300, responded=True):
        return {"digit": 5, "is_nogo": False, "responded": responded, "rt_ms": rt_ms}

    def _nogo(self, responded=False):
        return {"digit": 3, "is_nogo": True, "responded": responded, "rt_ms": None}

    def test_no_errors(self):
        trials = [self._go(), self._go(), self._nogo()]
        result = compute_sart_summary(trials)
        assert result["commission_errors"] == 0
        assert result["omission_errors"] == 0

    def test_commission_error_counted(self):
        trials = [self._nogo(responded=True)]
        result = compute_sart_summary(trials)
        assert result["commission_errors"] == 1

    def test_omission_error_counted(self):
        trials = [self._go(responded=False)]
        result = compute_sart_summary(trials)
        assert result["omission_errors"] == 1

    def test_go_median_rt(self):
        trials = [self._go(rt_ms=200), self._go(rt_ms=400), self._go(rt_ms=300)]
        result = compute_sart_summary(trials)
        assert result["go_median_rt"] == 300

    def test_go_rt_sd_is_none_for_single_trial(self):
        trials = [self._go(rt_ms=300)]
        result = compute_sart_summary(trials)
        assert result["go_rt_sd"] is None

    def test_post_error_slowing_none_if_fewer_than_three_errors(self):
        trials = [self._nogo(responded=True), self._go(rt_ms=300)]
        result = compute_sart_summary(trials)
        assert result["post_error_slowing"] is None

    def test_post_error_slowing_computed_with_three_errors(self):
        # 3 commission errors followed by go trials with RT 500ms (vs overall 300ms)
        trials = []
        for _ in range(3):
            trials.append(self._nogo(responded=True))
            trials.append(self._go(rt_ms=500))
        result = compute_sart_summary(trials)
        # go_median_rt would be 500 (all go trials are 500ms)
        # post_error_slowing = 500 - 500 = 0
        assert result["post_error_slowing"] is not None
        assert result["commission_errors"] == 3

    def test_empty_trials(self):
        result = compute_sart_summary([])
        assert result["commission_errors"] == 0
        assert result["go_median_rt"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Mood
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeMoodSummary:
    def test_extracts_all_four_dimensions(self):
        trials = [{"valence": 4, "arousal": 3, "stress": 2, "sharpness": 5}]
        result = compute_mood_summary(trials)
        assert result == {"valence": 4, "arousal": 3, "stress": 2, "sharpness": 5}

    def test_empty_trials_returns_none(self):
        result = compute_mood_summary([])
        assert result == {"valence": None, "arousal": None, "stress": None, "sharpness": None}

    def test_uses_first_trial(self):
        trials = [
            {"valence": 1, "arousal": 1, "stress": 1, "sharpness": 1},
            {"valence": 5, "arousal": 5, "stress": 5, "sharpness": 5},
        ]
        result = compute_mood_summary(trials)
        assert result["valence"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Flanker
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeFlankerSummary:
    def _trial(self, is_congruent, rt_ms=300, correct=True, responded=True):
        return {
            "is_congruent": is_congruent,
            "responded": responded,
            "correct": correct,
            "rt_ms": rt_ms,
        }

    def test_conflict_effect_equals_incongruent_minus_congruent(self):
        trials = [
            self._trial(True, rt_ms=250),
            self._trial(False, rt_ms=350),
        ]
        result = compute_flanker_summary(trials)
        assert result["conflict_effect_ms"] == pytest.approx(100.0)

    def test_congruent_accuracy(self):
        trials = [
            self._trial(True, correct=True),
            self._trial(True, correct=False),
        ]
        result = compute_flanker_summary(trials)
        assert result["congruent_accuracy"] == pytest.approx(0.5)

    def test_incongruent_accuracy(self):
        trials = [
            self._trial(False, correct=True),
            self._trial(False, correct=True),
            self._trial(False, correct=False),
        ]
        result = compute_flanker_summary(trials)
        assert result["incongruent_accuracy"] == pytest.approx(2 / 3)

    def test_none_when_no_congruent_trials(self):
        trials = [self._trial(False, rt_ms=300)]
        result = compute_flanker_summary(trials)
        assert result["congruent_median_rt"] is None
        assert result["conflict_effect_ms"] is None

    def test_empty_trials(self):
        result = compute_flanker_summary([])
        assert result["congruent_median_rt"] is None
        assert result["incongruent_median_rt"] is None
        assert result["conflict_effect_ms"] is None

    def test_mixed_trial_set(self):
        trials = [
            self._trial(True, rt_ms=200, correct=True),
            self._trial(True, rt_ms=300, correct=True),
            self._trial(False, rt_ms=350, correct=True),
            self._trial(False, rt_ms=450, correct=False),
        ]
        result = compute_flanker_summary(trials)
        assert result["congruent_median_rt"] == 250
        assert result["incongruent_median_rt"] == 400
        assert result["conflict_effect_ms"] == pytest.approx(150.0)
        assert result["congruent_accuracy"] == 1.0
        assert result["incongruent_accuracy"] == 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Digit Symbol
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeDigitSymbolSummary:
    def _trial(self, correct=True, responded=True):
        return {"correct": correct, "responded": responded}

    def test_total_correct_and_errors(self):
        trials = [self._trial(True), self._trial(True), self._trial(False)]
        result = compute_digit_symbol_summary(trials)
        assert result["total_correct"] == 2
        assert result["total_errors"] == 1

    def test_correct_per_minute_formula(self):
        trials = [self._trial(True)] * 30
        result = compute_digit_symbol_summary(trials, duration_ms=60_000)
        assert result["correct_per_minute"] == pytest.approx(30.0)

    def test_correct_per_minute_none_without_duration(self):
        trials = [self._trial(True)] * 10
        result = compute_digit_symbol_summary(trials)
        assert result["correct_per_minute"] is None

    def test_error_rate(self):
        trials = [self._trial(True), self._trial(False)]
        result = compute_digit_symbol_summary(trials)
        assert result["error_rate"] == pytest.approx(0.5)

    def test_error_rate_none_for_empty_trials(self):
        result = compute_digit_symbol_summary([])
        assert result["error_rate"] is None

    def test_correct_per_minute_with_non_60s_duration(self):
        # 20 correct in 30 seconds = 40/min
        trials = [self._trial(True)] * 20
        result = compute_digit_symbol_summary(trials, duration_ms=30_000)
        assert result["correct_per_minute"] == pytest.approx(40.0)

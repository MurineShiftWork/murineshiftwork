"""Tests for flag_outlier_points — calibration data outlier detection."""

from murineshiftwork.logic.calibration import flag_outlier_points
from murineshiftwork.tasks._calibration_liquid_dynamic._calibration_liquid_dynamic import (
    _compute_n_pulses,
    _estimate_ul,
    _suggest_additional_times,
)

# Realistic setup-3 data: exponential, well-behaved
TIMES_S = [0.010, 0.028, 0.046, 0.064, 0.082]
GOOD_UL = [0.675, 2.075, 4.150, 6.525, 9.050]


def test_clean_data_no_outliers():
    mask, residuals = flag_outlier_points(TIMES_S, GOOD_UL, sigma_threshold=2.0)
    assert not mask.any(), (
        f"Clean exponential data should have no outliers, got mask={mask}"
    )


def test_injected_outlier_is_flagged():
    """A point far below the fitted curve should be detected."""
    ul_with_outlier = GOOD_UL.copy()
    ul_with_outlier[2] = 0.3  # should be ~4.15 µL, injected as 0.3 µL
    mask, residuals = flag_outlier_points(TIMES_S, ul_with_outlier, sigma_threshold=1.5)
    assert mask[2], f"Expected index 2 to be flagged; residuals={residuals}"


def test_injected_high_outlier_is_flagged():
    """A point far above the fitted curve should be detected."""
    ul_with_outlier = GOOD_UL.copy()
    ul_with_outlier[1] = 12.0  # should be ~2.08 µL, injected as 12 µL
    mask, residuals = flag_outlier_points(TIMES_S, ul_with_outlier, sigma_threshold=2.0)
    assert mask[1], f"Expected index 1 to be flagged; residuals={residuals}"


def test_fewer_than_three_points_returns_no_flags():
    """With < 3 points there is not enough data to fit — never flag."""
    mask, residuals = flag_outlier_points(
        [0.010, 0.046], [0.5, 2.0], sigma_threshold=2.0
    )
    assert not mask.any()
    assert len(residuals) == 2


def test_linear_data_no_spurious_flags():
    """Straight-line data should not trigger outliers (falls back to linear fit)."""
    times_s = [0.010, 0.028, 0.046, 0.064, 0.082]
    ul_values = [float(t * 20) for t in times_s]  # perfect linear
    mask, _ = flag_outlier_points(times_s, ul_values, sigma_threshold=2.0)
    assert not mask.any()


def test_sigma_threshold_controls_sensitivity():
    """Higher threshold should flag fewer points."""
    ul_with_outlier = GOOD_UL.copy()
    ul_with_outlier[2] = 0.3
    mask_tight, _ = flag_outlier_points(TIMES_S, ul_with_outlier, sigma_threshold=1.5)
    mask_loose, _ = flag_outlier_points(TIMES_S, ul_with_outlier, sigma_threshold=4.0)
    # At threshold=1.5 the outlier must be flagged; at 4.0 it might not be
    assert mask_tight[2]
    assert mask_tight.sum() >= mask_loose.sum()


def test_outlier_mask_and_residuals_same_length():
    mask, residuals = flag_outlier_points(TIMES_S, GOOD_UL)
    assert len(mask) == len(TIMES_S)
    assert len(residuals) == len(TIMES_S)


# ---------------------------------------------------------------------------
# Helper function tests (no hardware)


class TestComputeNPulses:
    def test_large_drop_needs_few_pulses(self):
        n = _compute_n_pulses(
            8.0, scale_noise_g=0.05, min_snr=10, min_pulses=50, max_pulses=1000
        )
        assert n <= 100, f"Expected ≤100 pulses for 8µL/drop, got {n}"

    def test_tiny_drop_needs_many_pulses(self):
        n = _compute_n_pulses(
            0.5, scale_noise_g=0.05, min_snr=10, min_pulses=50, max_pulses=1000
        )
        assert n >= 500, f"Expected ≥500 pulses for 0.5µL/drop, got {n}"

    def test_respects_min_pulses(self):
        n = _compute_n_pulses(
            100.0,
            scale_noise_g=0.05,
            min_snr=10,
            min_pulses=50,
            max_pulses=1000,
        )
        assert n >= 50

    def test_respects_max_pulses(self):
        n = _compute_n_pulses(
            0.001,
            scale_noise_g=0.05,
            min_snr=10,
            min_pulses=50,
            max_pulses=1000,
        )
        assert n <= 1000

    def test_zero_expected_ul_returns_max(self):
        n = _compute_n_pulses(
            0.0, scale_noise_g=0.05, min_snr=10, min_pulses=50, max_pulses=1000
        )
        assert n == 1000


class TestEstimateUl:
    def test_no_data_returns_default(self):
        result = _estimate_ul(0.05, [], [])
        assert result > 0

    def test_scales_linearly_from_single_point(self):
        result = _estimate_ul(0.08, [0.04], [4.0])
        assert abs(result - 8.0) < 0.5  # roughly double

    def test_uses_fit_with_three_points(self):
        times = [0.010, 0.046, 0.082]
        ul = [0.675, 4.15, 9.05]
        result = _estimate_ul(0.028, times, ul)
        assert 1.0 < result < 4.0  # should be between first and middle point


class TestSuggestAdditionalTimes:
    def test_well_covered_range_returns_empty(self):
        # Five points that adequately cover 0.5–9 µL range
        times = [0.010, 0.028, 0.046, 0.064, 0.082]
        ul = [0.675, 2.075, 4.15, 6.525, 9.05]
        suggestions = _suggest_additional_times(
            times,
            ul,
            min_ul=0.5,
            max_ul=9.0,
            time_min_s=0.005,
            time_max_s=0.150,
            n_target=5,
        )
        assert len(suggestions) == 0, (
            f"Fully covered range should need no extras: {suggestions}"
        )

    def test_too_few_points_suggests_more(self):
        times = [0.010, 0.082]
        ul = [0.5, 9.0]
        suggestions = _suggest_additional_times(
            times,
            ul,
            min_ul=0.5,
            max_ul=9.0,
            time_min_s=0.005,
            time_max_s=0.150,
            n_target=5,
        )
        assert len(suggestions) > 0

    def test_does_not_suggest_existing_times(self):
        times = [0.010, 0.046, 0.082]
        ul = [0.675, 4.15, 9.05]
        suggestions = _suggest_additional_times(
            times,
            ul,
            min_ul=0.5,
            max_ul=9.0,
            time_min_s=0.005,
            time_max_s=0.150,
            n_target=5,
        )
        for s in suggestions:
            assert s not in times, f"Suggested time {s} already measured"

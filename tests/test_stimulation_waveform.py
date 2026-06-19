"""Tests for waveform generation in hardware.stimulation.

Covers _ramp_envelope, generate_waveform_voltages, and the Stimulation class
waveform-param integration. Runs without a physical PulsePal or the pypulsepal
package installed by stubbing sys.modules before import.
"""

from __future__ import annotations

import math
import sys
from unittest.mock import MagicMock

import pytest

# Stub pypulsepal so stimulation.py can be imported without the hardware package.
# If the real package is already installed it takes precedence.
if "pypulsepal" not in sys.modules:
    sys.modules["pypulsepal"] = MagicMock()

from murineshiftwork.hardware.stimulation import (
    _PULSEPAL_SAMPLE_RATE,
    WAVEFORM_LINEAR,
    WAVEFORM_RAISED_COSINE,
    WAVEFORM_SINE,
    Stimulation,
    _ramp_envelope,
    generate_waveform_voltages,
)

# ---------------------------------------------------------------------------
# _ramp_envelope: boundary conditions


def test_ramp_envelope_zero_samples_returns_empty():
    assert _ramp_envelope(0, WAVEFORM_LINEAR, rising=True) == []


def test_ramp_envelope_one_sample_returns_peak():
    assert _ramp_envelope(1, WAVEFORM_LINEAR, rising=True) == [1.0]
    assert _ramp_envelope(1, WAVEFORM_LINEAR, rising=False) == [1.0]


def test_ramp_envelope_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown waveform type"):
        _ramp_envelope(10, "triangle", rising=True)


# ---------------------------------------------------------------------------
# _ramp_envelope: rising endpoints for all types


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_ramp_envelope_rising_starts_at_zero(ramp_type):
    vals = _ramp_envelope(20, ramp_type, rising=True)
    assert vals[0] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_ramp_envelope_rising_ends_at_one(ramp_type):
    vals = _ramp_envelope(20, ramp_type, rising=True)
    assert vals[-1] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_ramp_envelope_falling_starts_at_one(ramp_type):
    vals = _ramp_envelope(20, ramp_type, rising=False)
    assert vals[0] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_ramp_envelope_falling_ends_at_zero(ramp_type):
    vals = _ramp_envelope(20, ramp_type, rising=False)
    assert vals[-1] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_ramp_envelope_falling_is_reversed_rising(ramp_type):
    n = 20
    rising = _ramp_envelope(n, ramp_type, rising=True)
    falling = _ramp_envelope(n, ramp_type, rising=False)
    assert falling == pytest.approx(list(reversed(rising)), abs=1e-9)


# ---------------------------------------------------------------------------
# _ramp_envelope: known values at n=5


def test_ramp_envelope_linear_known_values():
    vals = _ramp_envelope(5, WAVEFORM_LINEAR, rising=True)
    assert vals == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0], abs=1e-9)


def test_ramp_envelope_sine_known_values():
    vals = _ramp_envelope(5, WAVEFORM_SINE, rising=True)
    expected = [math.sin(math.pi / 2 * t) for t in [0, 0.25, 0.5, 0.75, 1.0]]
    assert vals == pytest.approx(expected, abs=1e-9)


def test_ramp_envelope_raised_cosine_known_values():
    vals = _ramp_envelope(5, WAVEFORM_RAISED_COSINE, rising=True)
    expected = [(1 - math.cos(math.pi * t)) / 2 for t in [0, 0.25, 0.5, 0.75, 1.0]]
    assert vals == pytest.approx(expected, abs=1e-9)


def test_ramp_envelope_raised_cosine_midpoint_is_half():
    # Raised cosine at t=0.5 is exactly 0.5 by definition
    vals = _ramp_envelope(5, WAVEFORM_RAISED_COSINE, rising=True)
    assert vals[2] == pytest.approx(0.5, abs=1e-9)


# ---------------------------------------------------------------------------
# generate_waveform_voltages: sample count and duration


def test_generate_waveform_sample_count_three_phases():
    sr = 1000  # use 1 kHz for easy mental arithmetic
    v, dur = generate_waveform_voltages(
        1.0, WAVEFORM_LINEAR, 0.01, 0.03, WAVEFORM_LINEAR, 0.01, sr
    )
    assert len(v) == 10 + 30 + 10


def test_generate_waveform_duration_matches_sample_count():
    sr = 1000
    v, dur = generate_waveform_voltages(
        1.0, WAVEFORM_LINEAR, 0.01, 0.03, WAVEFORM_LINEAR, 0.01, sr
    )
    assert dur == pytest.approx(len(v) / sr, abs=1e-9)


def test_generate_waveform_center_only():
    sr = 1000
    v, dur = generate_waveform_voltages(2.0, None, 0.0, 0.05, None, 0.0, sr)
    assert len(v) == 50
    assert all(s == pytest.approx(2.0) for s in v)


def test_generate_waveform_on_ramp_only():
    sr = 1000
    v, dur = generate_waveform_voltages(1.5, WAVEFORM_LINEAR, 0.01, 0.0, None, 0.0, sr)
    assert len(v) == 10
    assert v[0] == pytest.approx(0.0, abs=1e-9)
    assert v[-1] == pytest.approx(1.5, abs=1e-9)


def test_generate_waveform_off_ramp_only():
    sr = 1000
    v, dur = generate_waveform_voltages(1.5, None, 0.0, 0.0, WAVEFORM_LINEAR, 0.01, sr)
    assert len(v) == 10
    assert v[0] == pytest.approx(1.5, abs=1e-9)
    assert v[-1] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# generate_waveform_voltages: endpoint values


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_generate_waveform_first_sample_near_zero_with_on_ramp(ramp_type):
    v, _ = generate_waveform_voltages(1.5, ramp_type, 0.005, 0.005, None, 0.0)
    assert v[0] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    "ramp_type", [WAVEFORM_LINEAR, WAVEFORM_SINE, WAVEFORM_RAISED_COSINE]
)
def test_generate_waveform_last_sample_near_zero_with_off_ramp(ramp_type):
    v, _ = generate_waveform_voltages(1.5, None, 0.0, 0.005, ramp_type, 0.005)
    assert v[-1] == pytest.approx(0.0, abs=1e-6)


def test_generate_waveform_center_samples_at_target():
    sr = 1000
    target = 1.234
    v, _ = generate_waveform_voltages(
        target, WAVEFORM_LINEAR, 0.01, 0.02, WAVEFORM_LINEAR, 0.01, sr
    )
    center_samples = v[10:30]
    assert all(s == pytest.approx(target, rel=1e-6) for s in center_samples)


def test_generate_waveform_scales_by_target_voltage():
    v1, _ = generate_waveform_voltages(1.0, WAVEFORM_LINEAR, 0.01, 0.0, None, 0.0, 1000)
    v2, _ = generate_waveform_voltages(2.0, WAVEFORM_LINEAR, 0.01, 0.0, None, 0.0, 1000)
    assert [pytest.approx(a * 2) for a in v1] == [pytest.approx(b) for b in v2]


# ---------------------------------------------------------------------------
# generate_waveform_voltages: pure bump (center_duration=0)


def test_generate_waveform_pure_bump_no_flat_top():
    sr = 1000
    v, dur = generate_waveform_voltages(
        1.0, WAVEFORM_SINE, 0.01, 0.0, WAVEFORM_SINE, 0.01, sr
    )
    assert len(v) == 20


def test_generate_waveform_pure_bump_starts_and_ends_at_zero():
    v, _ = generate_waveform_voltages(
        1.5, WAVEFORM_RAISED_COSINE, 0.005, 0.0, WAVEFORM_RAISED_COSINE, 0.005
    )
    assert v[0] == pytest.approx(0.0, abs=1e-6)
    assert v[-1] == pytest.approx(0.0, abs=1e-6)


def test_generate_waveform_pure_bump_peak_at_target():
    v, _ = generate_waveform_voltages(
        1.5, WAVEFORM_RAISED_COSINE, 0.005, 0.0, WAVEFORM_RAISED_COSINE, 0.005
    )
    assert max(v) == pytest.approx(1.5, abs=1e-3)


# ---------------------------------------------------------------------------
# generate_waveform_voltages: default sample rate is 20 kHz


def test_generate_waveform_default_sample_rate():
    v, dur = generate_waveform_voltages(
        1.0, WAVEFORM_LINEAR, 0.001, 0.003, WAVEFORM_LINEAR, 0.001
    )
    assert len(v) == _PULSEPAL_SAMPLE_RATE * 5 // 1000  # 5 ms * 20 kHz = 100 samples


# ---------------------------------------------------------------------------
# Stimulation.__init__ with waveform params


def _make_stim(**waveform_kwargs):
    return Stimulation(
        port="/dev/null",
        in_dict={
            "channels_stimulation": [0],
            "channels_ttl_copy": [],
            "pulse_frequency": 40,
            **waveform_kwargs,
        },
    )


def test_stimulation_waveform_overrides_pulse_duration():
    stim = _make_stim(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        waveform_off_ramp_type=WAVEFORM_LINEAR,
        waveform_off_ramp_duration_s=0.001,
    )
    expected_total = 0.005
    assert stim.in_dict["pulse_duration"] == pytest.approx(expected_total, abs=1e-4)


def test_stimulation_waveform_ipi_uses_waveform_duration():
    stim = _make_stim(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        waveform_off_ramp_type=WAVEFORM_LINEAR,
        waveform_off_ramp_duration_s=0.001,
    )
    ch_params = stim._channel_params[0]
    expected_ipi = round(1 / 40 - ch_params["phase1Duration"], 3)
    assert ch_params["interPulseInterval"] == pytest.approx(expected_ipi, abs=1e-4)


def test_stimulation_waveform_too_long_raises():
    with pytest.raises(ValueError, match="Waveform duration"):
        _make_stim(
            waveform_on_ramp_type=WAVEFORM_LINEAR,
            waveform_on_ramp_duration_s=0.020,
            waveform_center_duration_s=0.010,
            waveform_off_ramp_type=WAVEFORM_LINEAR,
            waveform_off_ramp_duration_s=0.005,
            # 35 ms total > 25 ms cycle at 40 Hz
        )


def test_stimulation_no_waveform_keeps_explicit_pulse_duration():
    stim = Stimulation(
        port="/dev/null",
        in_dict={"channels_stimulation": [0], "pulse_duration": 0.003},
    )
    assert stim.in_dict["pulse_duration"] == pytest.approx(0.003)


def test_stimulation_use_custom_waveform_true_when_on_ramp_set():
    stim = _make_stim(
        waveform_on_ramp_type=WAVEFORM_SINE,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    assert stim._use_custom_waveform is True


def test_stimulation_use_custom_waveform_true_when_only_off_ramp_set():
    stim = _make_stim(
        waveform_off_ramp_type=WAVEFORM_SINE,
        waveform_off_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    assert stim._use_custom_waveform is True


def test_stimulation_use_custom_waveform_false_by_default():
    stim = Stimulation(port="/dev/null")
    assert stim._use_custom_waveform is False


def test_stimulation_waveform_params_not_left_in_in_dict():
    stim = _make_stim(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    for key in (
        "waveform_on_ramp_type",
        "waveform_on_ramp_duration_s",
        "waveform_center_duration_s",
        "waveform_off_ramp_type",
        "waveform_off_ramp_duration_s",
    ):
        assert key not in stim.in_dict


# ---------------------------------------------------------------------------
# Stimulation.setup_custom_waveform


def _make_stim_with_mock_pp(**waveform_kwargs):
    stim = _make_stim(**waveform_kwargs)
    stim.pulsepal = MagicMock()
    return stim


def test_setup_custom_waveform_calls_upload():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform(slot=0)
    stim.pulsepal.upload_custom_waveform.assert_called_once()


def test_setup_custom_waveform_uses_correct_slot():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform(slot=1)
    _, kwargs = stim.pulsepal.upload_custom_waveform.call_args
    assert kwargs["pulse_train_id"] == 1


def test_setup_custom_waveform_sample_width_matches_sample_rate():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform()
    _, kwargs = stim.pulsepal.upload_custom_waveform.call_args
    assert kwargs["pulse_width"] == pytest.approx(1.0 / _PULSEPAL_SAMPLE_RATE)


def test_setup_custom_waveform_sets_custom_train_id_1indexed():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform(slot=0)
    calls = stim.pulsepal.program_one_param.call_args_list
    custom_id_calls = [c for c in calls if c.args[1] == "customTrainID"]
    assert custom_id_calls
    assert custom_id_calls[0].args[2] == 1  # slot 0 → customTrainID 1


def test_setup_custom_waveform_sets_custom_train_target_zero():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    target_calls = [c for c in calls if c.args[1] == "customTrainTarget"]
    assert target_calls
    assert target_calls[0].args[2] == 0


def test_setup_custom_waveform_sets_custom_train_loop_one():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    loop_calls = [c for c in calls if c.args[1] == "customTrainLoop"]
    assert loop_calls
    assert loop_calls[0].args[2] == 1


def test_setup_custom_waveform_sets_phase1_duration_to_sample_period():
    """phase1Duration must be one sample period so every sample plays correctly."""
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    p1d_calls = [c for c in calls if c.args[1] == "phase1Duration"]
    assert p1d_calls
    assert p1d_calls[0].args[2] == pytest.approx(1.0 / _PULSEPAL_SAMPLE_RATE)


def test_setup_custom_waveform_sets_inter_pulse_interval_zero():
    """IPI must be 0 because the loop gap is embedded in the zero-padded waveform."""
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    ipi_calls = [c for c in calls if c.args[1] == "interPulseInterval"]
    assert ipi_calls
    assert ipi_calls[0].args[2] == pytest.approx(0.0)


def test_setup_custom_waveform_pads_to_full_cycle():
    """Uploaded waveform must be exactly one pulse cycle long for looping at pulse_frequency."""
    pulse_frequency = 40  # 25 ms cycle = 500 samples at 20 kHz
    stim = Stimulation(
        port="/dev/null",
        in_dict={
            "channels_stimulation": [0],
            "channels_ttl_copy": [],
            "pulse_frequency": pulse_frequency,
            "waveform_on_ramp_type": WAVEFORM_LINEAR,
            "waveform_on_ramp_duration_s": 0.001,
            "waveform_center_duration_s": 0.003,
            "waveform_off_ramp_type": WAVEFORM_LINEAR,
            "waveform_off_ramp_duration_s": 0.001,
        },
    )
    stim.pulsepal = MagicMock()
    stim.setup_custom_waveform()
    _, kwargs = stim.pulsepal.upload_custom_waveform.call_args
    uploaded = kwargs["pulse_voltages"]
    expected_n = round(_PULSEPAL_SAMPLE_RATE / pulse_frequency)
    assert len(uploaded) == expected_n


def test_setup_custom_waveform_padded_tail_is_zero():
    """Trailing silence samples must be 0V (not residual ramp voltage)."""
    pulse_frequency = 40
    stim = Stimulation(
        port="/dev/null",
        in_dict={
            "channels_stimulation": [0],
            "channels_ttl_copy": [],
            "pulse_frequency": pulse_frequency,
            "waveform_on_ramp_type": WAVEFORM_LINEAR,
            "waveform_on_ramp_duration_s": 0.001,
            "waveform_center_duration_s": 0.003,
            "waveform_off_ramp_type": WAVEFORM_LINEAR,
            "waveform_off_ramp_duration_s": 0.001,
        },
    )
    stim.pulsepal = MagicMock()
    stim.setup_custom_waveform()
    _, kwargs = stim.pulsepal.upload_custom_waveform.call_args
    uploaded = kwargs["pulse_voltages"]
    n_shaped = round((0.001 + 0.003 + 0.001) * _PULSEPAL_SAMPLE_RATE)
    tail = uploaded[n_shaped:]
    assert all(v == pytest.approx(0.0) for v in tail)


def test_setup_custom_waveform_returns_total_duration():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        waveform_off_ramp_type=WAVEFORM_LINEAR,
        waveform_off_ramp_duration_s=0.001,
    )
    result = stim.setup_custom_waveform()
    assert result == pytest.approx(0.005, abs=1e-4)


def test_setup_custom_waveform_noop_without_waveform_params():
    stim = Stimulation(port="/dev/null", in_dict={"channels_stimulation": [0]})
    stim.pulsepal = MagicMock()
    result = stim.setup_custom_waveform()
    assert result == 0.0
    stim.pulsepal.upload_custom_waveform.assert_not_called()
    stim.pulsepal.program_one_param.assert_not_called()


def test_setup_custom_waveform_gated_sets_large_pulse_train_duration():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        trigger_mode="gated",
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    ptd_calls = [c for c in calls if c.args[1] == "pulseTrainDuration"]
    assert ptd_calls
    assert ptd_calls[0].args[2] == pytest.approx(3600.0)


def test_setup_custom_waveform_non_gated_no_pulse_train_duration_override():
    stim = _make_stim_with_mock_pp(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        trigger_mode="normal",
    )
    stim.setup_custom_waveform()
    calls = stim.pulsepal.program_one_param.call_args_list
    ptd_calls = [c for c in calls if c.args[1] == "pulseTrainDuration"]
    assert not ptd_calls


def test_connect_sets_continuous_zero_in_gated_mode():
    """Gated mode must use set_continuous=0 so the channel starts from sample 0
    on each gate rising edge. set_continuous=1 would cause a phase-offset blip
    on the first gate open because the channel runs internally between gates."""
    stim = _make_stim(
        waveform_on_ramp_type=WAVEFORM_LINEAR,
        waveform_on_ramp_duration_s=0.001,
        waveform_center_duration_s=0.003,
        trigger_mode="gated",
        trigger_channels_for_stimulation=[0],
    )
    mock_pp = MagicMock()
    mock_pp.nr_output_channels = 4
    mock_pp.channel_configs = [MagicMock() for _ in range(4)]
    mock_pp.trigger_configs = [MagicMock() for _ in range(2)]
    stim.connect(handle=mock_pp)
    set_cont_calls = mock_pp.set_continuous.call_args_list
    stim_ch = stim.in_dict["channels_stimulation"][0]
    stim_ch_calls = [
        c
        for c in set_cont_calls
        if c.kwargs.get("channel") == stim_ch or (c.args and c.args[0] == stim_ch)
    ]
    assert stim_ch_calls, (
        "set_continuous must be called for stim channels in gated mode"
    )
    states = [
        c.kwargs.get("state", c.args[1] if len(c.args) > 1 else None)
        for c in stim_ch_calls
    ]
    assert all(s == 0 for s in states), (
        f"set_continuous must be 0 in gated mode, got {states}"
    )


def test_connect_still_sets_continuous_for_ttl_copy_in_gated_mode():
    stim = Stimulation(
        port="/dev/null",
        in_dict={
            "channels_stimulation": [0],
            "channels_ttl_copy": [3],
            "pulse_frequency": 40,
            "trigger_mode": "gated",
            "trigger_channels_for_stimulation": [0],
            "waveform_on_ramp_type": WAVEFORM_LINEAR,
            "waveform_on_ramp_duration_s": 0.001,
            "waveform_center_duration_s": 0.003,
        },
    )
    mock_pp = MagicMock()
    mock_pp.nr_output_channels = 4
    mock_pp.channel_configs = [MagicMock() for _ in range(4)]
    mock_pp.trigger_configs = [MagicMock() for _ in range(2)]
    stim.connect(handle=mock_pp)
    set_cont_calls = mock_pp.set_continuous.call_args_list
    copy_ch_calls = [
        c
        for c in set_cont_calls
        if c.kwargs.get("channel") == 3 or (c.args and c.args[0] == 3)
    ]
    assert copy_ch_calls, "set_continuous must be called for TTL copy channels"
    states = [
        c.kwargs.get("state", c.args[1] if len(c.args) > 1 else None)
        for c in copy_ch_calls
    ]
    assert all(s == 0 for s in states), (
        f"set_continuous must be 0 in gated mode for TTL copy channels too, got {states}"
    )

"""Tests for unified optotagging task and logic/stimulation.py."""

import json
from unittest.mock import MagicMock, call, patch

import pytest

pytest.importorskip("pypulsepal")  # skip whole module if pypulsepal not installed

import pytest

from murineshiftwork.hardware.stimulation import (
    DORIC_MAX_CURRENT_MA,
    DORIC_MAX_VOLTAGE,
    Stimulation,
    power_to_voltage,
)
from murineshiftwork.tasks.optotagging.optotagging import OptoTaggingRecord

# ---------------------------------------------------------------------------
# power_to_voltage
# ---------------------------------------------------------------------------


def test_power_to_voltage_zero():
    assert power_to_voltage(0.0) == 0.0


def test_power_to_voltage_one_equals_max():
    assert power_to_voltage(1.0) == pytest.approx(DORIC_MAX_VOLTAGE)


def test_power_to_voltage_midpoint():
    assert power_to_voltage(0.5) == pytest.approx(DORIC_MAX_VOLTAGE * 0.5, rel=1e-4)


def test_power_to_voltage_consistent_with_constants():
    # DORIC_MAX_VOLTAGE = DORIC_MAX_CURRENT_MA / DORIC_CURRENT_SENSITIVITY
    assert pytest.approx(DORIC_MAX_CURRENT_MA / 80.0) == DORIC_MAX_VOLTAGE


# ---------------------------------------------------------------------------
# Stimulation._validate_power
# ---------------------------------------------------------------------------


def test_validate_power_accepts_zero():
    Stimulation._validate_power(0.0)


def test_validate_power_accepts_one():
    Stimulation._validate_power(1.0)


def test_validate_power_accepts_midpoint():
    Stimulation._validate_power(0.5)


def test_validate_power_rejects_negative():
    with pytest.raises(ValueError, match="laser_power must be in"):
        Stimulation._validate_power(-0.1)


def test_validate_power_rejects_above_one():
    with pytest.raises(ValueError, match="laser_power must be in"):
        Stimulation._validate_power(1.001)


# ---------------------------------------------------------------------------
# Stimulation.__init__ — channel param setup, no connect() called
# ---------------------------------------------------------------------------


def test_stimulation_laser_power_none_uses_fixed_voltage():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": None})
    ch = stim.in_dict["channels_stimulation"][0]
    assert stim._channel_params[ch]["phase1Voltage"] == 5


def test_stimulation_laser_power_float_uses_doric_voltage():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    ch = stim.in_dict["channels_stimulation"][0]
    assert stim._channel_params[ch]["phase1Voltage"] == pytest.approx(
        power_to_voltage(0.5), rel=1e-4
    )


def test_stimulation_laser_power_one_uses_max_voltage():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 1.0})
    ch = stim.in_dict["channels_stimulation"][0]
    assert stim._channel_params[ch]["phase1Voltage"] == pytest.approx(DORIC_MAX_VOLTAGE)


def test_stimulation_invalid_laser_power_raises_on_init():
    with pytest.raises(ValueError):
        Stimulation(port="/dev/null", in_dict={"laser_power": 2.0})


def test_stimulation_in_dict_isolated_between_instances():
    """Mutating one instance must not affect another — class-variable bug regression."""
    s1 = Stimulation(port="/dev/null", in_dict={"pulse_duration": 0.001})
    s2 = Stimulation(port="/dev/null", in_dict={"pulse_duration": 0.005})
    assert s1.in_dict["pulse_duration"] == 0.001
    assert s2.in_dict["pulse_duration"] == 0.005


def test_stimulation_channel_params_built_for_stim_channel():
    stim = Stimulation(
        port="/dev/null",
        in_dict={"channels_stimulation": [2], "channels_ttl_copy": [3]},
    )
    assert 2 in stim._channel_params
    assert 3 in stim._channel_params


def test_stimulation_ipi_computed_correctly():
    stim = Stimulation(
        port="/dev/null",
        in_dict={"pulse_frequency": 40, "pulse_duration": 0.001},
    )
    ch = stim.in_dict["channels_stimulation"][0]
    expected_ipi = round(1 / 40 - 0.001, 3)
    assert stim._channel_params[ch]["interPulseInterval"] == pytest.approx(
        expected_ipi, abs=1e-4
    )


# ---------------------------------------------------------------------------
# Stimulation.set_power
# ---------------------------------------------------------------------------


def test_set_power_updates_in_dict():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    stim.set_power(0.8)
    assert stim.in_dict["laser_power"] == pytest.approx(0.8)


def test_set_power_updates_channel_params():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    stim.set_power(0.8)
    ch = stim.in_dict["channels_stimulation"][0]
    assert stim._channel_params[ch]["phase1Voltage"] == pytest.approx(
        power_to_voltage(0.8), rel=1e-4
    )


def test_set_power_rejects_invalid():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    with pytest.raises(ValueError):
        stim.set_power(1.5)


def test_set_power_syncs_to_pulsepal_when_connected():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    mock_pp = MagicMock()
    stim.pulsePal = mock_pp
    stim.set_power(0.8)
    mock_pp.program_one_param.assert_called_once_with(
        channel=stim.in_dict["channels_stimulation"][0],
        param_name="phase1Voltage",
        param_value=pytest.approx(power_to_voltage(0.8), rel=1e-4),
    )


def test_set_power_no_sync_when_pulsePal_none():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    stim.set_power(0.8)  # must not raise even though pulsePal is None


# ---------------------------------------------------------------------------
# Stimulation.set_pulse_params
# ---------------------------------------------------------------------------


def test_set_pulse_params_updates_duration():
    stim = Stimulation(port="/dev/null", in_dict={"pulse_duration": 0.001})
    stim.set_pulse_params(pulse_duration=0.005)
    assert stim.in_dict["pulse_duration"] == pytest.approx(0.005)


def test_set_pulse_params_updates_frequency():
    stim = Stimulation(port="/dev/null")
    stim.set_pulse_params(pulse_frequency=20.0)
    assert stim.in_dict["pulse_frequency"] == pytest.approx(20.0)


def test_set_pulse_params_updates_laser_power():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.3})
    stim.set_pulse_params(laser_power=0.7)
    assert stim.in_dict["laser_power"] == pytest.approx(0.7)


def test_set_pulse_params_rejects_invalid_power():
    stim = Stimulation(port="/dev/null", in_dict={"laser_power": 0.5})
    with pytest.raises(ValueError):
        stim.set_pulse_params(laser_power=-0.1)


# ---------------------------------------------------------------------------
# OptoTaggingRecord
# ---------------------------------------------------------------------------


def _make_trial_data(first_state="barcode_start_s0"):
    return {"States timestamps": {first_state: [0.0, 0.1]}, "Events timestamps": {}}


def _make_record(tmp_path, protocol="power_ramp"):
    basename = "mouse_01__20260524_143022_123456__optotagging"
    session_file_path = str(tmp_path / basename)
    return OptoTaggingRecord(session_file_path, protocol)


def test_record_update_barcode_trial_type(tmp_path):
    rec = _make_record(tmp_path)
    rec.update(
        trial_index=0,
        trial_data=_make_trial_data("barcode_start_s0"),
        barcode_value=42,
        barcode_wall_time=1.0,
        protocol="power_ramp",
    )
    assert rec.trial_data[0]["info"]["trial_type"] == "barcode"


def test_record_update_task_trial_type(tmp_path):
    rec = _make_record(tmp_path)
    rec.update(
        trial_index=1,
        trial_data=_make_trial_data("trial_onset"),
        barcode_value=None,
        barcode_wall_time=None,
        protocol="power_ramp",
    )
    assert rec.trial_data[0]["info"]["trial_type"] == "task"


def test_record_update_stores_protocol(tmp_path):
    rec = _make_record(tmp_path, protocol="my_protocol")
    rec.update(trial_index=0, trial_data=_make_trial_data(), protocol="my_protocol")
    assert rec.trial_data[0]["info"]["protocol"] == "my_protocol"


def test_record_update_stores_trial_index(tmp_path):
    rec = _make_record(tmp_path)
    rec.update(trial_index=7, trial_data=_make_trial_data(), protocol="p")
    assert rec.trial_data[0]["info"]["trial_index"] == 7


def test_record_update_stores_barcode_fields(tmp_path):
    rec = _make_record(tmp_path)
    rec.update(
        trial_index=0,
        trial_data=_make_trial_data(),
        barcode_value=99,
        barcode_wall_time=3.14,
        protocol="p",
    )
    assert rec.trial_data[0]["info"]["barcode_value"] == 99
    assert rec.trial_data[0]["info"]["barcode_wall_time"] == pytest.approx(3.14)


def test_record_accumulates_across_updates(tmp_path):
    rec = _make_record(tmp_path)
    for i in range(3):
        rec.update(trial_index=i, trial_data=_make_trial_data(), protocol="p")
    assert len(rec.trial_data) == 3


def test_record_instances_have_independent_trial_data(tmp_path):
    """Regression: class-variable list would share state between instances."""
    basename = str(tmp_path / "mouse_01__20260524_143022_123456__optotagging")
    r1 = OptoTaggingRecord(basename, "power_ramp")
    r2 = OptoTaggingRecord(basename, "following_test")
    r1.update(trial_index=0, trial_data=_make_trial_data(), protocol="p")
    assert len(r2.trial_data) == 0


def test_record_proto_base_includes_protocol_name(tmp_path):
    basename = str(tmp_path / "mouse_01__20260524_143022_123456__optotagging")
    rec = OptoTaggingRecord(basename, "power_ramp")
    assert "power_ramp" in rec.proto_base


def test_record_filename_includes_protocol_and_suffix(tmp_path):
    basename = str(tmp_path / "mouse_01__20260524_143022_123456__optotagging")
    rec = OptoTaggingRecord(basename, "power_ramp")
    assert rec.filename.endswith("power_ramp.msw.df.jsonl")


def test_record_save_writes_jsonl(tmp_path):
    _basename = "mouse_01__20260524_143022_123456__optotagging"
    rec = OptoTaggingRecord(str(tmp_path / _basename), "power_ramp")
    rec.update(
        trial_index=0,
        trial_data=_make_trial_data(),
        barcode_value=1,
        protocol="power_ramp",
    )
    rec.save()
    out = tmp_path / f"{_basename}__power_ramp" / f"{_basename}_power_ramp.msw.df.jsonl"
    assert out.exists()
    lines = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    trial_lines = [ln for ln in lines if "info" in ln]
    assert len(trial_lines) == 1
    assert trial_lines[0]["info"]["trial_index"] == 0


# ---------------------------------------------------------------------------
# needs_video detection (extracted from run_task logic)
# ---------------------------------------------------------------------------


def _needs_video(task_settings: dict) -> bool:
    defaults = task_settings.get("stimulation_defaults", {})
    protocols = task_settings.get("stimulation", {})
    return defaults.get("record_video", False) or any(
        (p or {}).get("record_video", False) for p in protocols.values()
    )


def test_needs_video_false_when_not_set():
    assert not _needs_video({})


def test_needs_video_false_when_explicitly_false():
    settings = {
        "stimulation_defaults": {"record_video": False},
        "stimulation": {"p1": {"record_video": False}},
    }
    assert not _needs_video(settings)


def test_needs_video_true_from_defaults():
    settings = {
        "stimulation_defaults": {"record_video": True},
        "stimulation": {"p1": {}},
    }
    assert _needs_video(settings)


def test_needs_video_true_from_single_protocol():
    settings = {
        "stimulation_defaults": {"record_video": False},
        "stimulation": {
            "p1": {"record_video": False},
            "p2": {"record_video": True},
        },
    }
    assert _needs_video(settings)


def test_needs_video_handles_none_protocol_value():
    settings = {
        "stimulation_defaults": {},
        "stimulation": {"p1": None},
    }
    assert not _needs_video(settings)


# ---------------------------------------------------------------------------
# Task._start_protocol_video — path construction
# ---------------------------------------------------------------------------


def _make_task_for_video(session_basename, subject, is_child=None):
    from murineshiftwork.tasks.optotagging.optotagging import Task

    # session_folder_relative mirrors the namespace: subject/acquisition/session
    acq_name = f"{subject}__{session_basename}__session_opto"
    session_folder_relative = f"{subject}/{acq_name}/{session_basename}"
    t = object.__new__(Task)
    t.input_kwargs = {
        "session_paths": {
            "session_basename": session_basename,
            "subject": subject,
            "session_file_path": f"/data/{session_folder_relative}/{session_basename}",
            "session_folder_relative": session_folder_relative,
        },
    }
    return t


def test_start_protocol_video_path():
    t = _make_task_for_video("sess_001", "mouse01")
    conductor = MagicMock()
    rel = t.input_kwargs["session_paths"]["session_folder_relative"]
    with patch("time.sleep"):
        t._start_protocol_video(conductor, "proto_40hz")
    conductor.initialize_acquisition.assert_called_once_with(
        acquisition_path=f"{rel}/sess_001__proto_40hz",
        acquisition_name="sess_001_proto_40hz",
    )


def test_start_protocol_video_calls_preview_then_recording():
    t = _make_task_for_video("sess_001", "mouse01")
    conductor = MagicMock()
    with patch("time.sleep"):
        t._start_protocol_video(conductor, "proto_40hz")
    assert conductor.method_calls[1] == call.start_preview()
    assert conductor.method_calls[2] == call.start_recording()


def test_start_protocol_video_sleeps_warmup():
    t = _make_task_for_video("sess_001", "mouse01")
    conductor = MagicMock()
    with patch("time.sleep") as mock_sleep:
        t._start_protocol_video(conductor, "proto_40hz", warmup_s=5.0)
    mock_sleep.assert_called_once_with(5.0)


# ---------------------------------------------------------------------------
# Protocol param merging (stimulation_defaults + per-protocol deep_merge)
# ---------------------------------------------------------------------------


def test_protocol_merge_defaults_fill_missing_keys():
    from murineshiftwork.logic.config.ini import deep_merge

    defaults = {"n_trials": 50, "iti": 1.0, "pulse_duration": 0.001}
    protocol = {"pulse_duration": 0.005}
    result = deep_merge(defaults, protocol)
    assert result["n_trials"] == 50
    assert result["pulse_duration"] == 0.005


def test_protocol_merge_protocol_beats_defaults():
    from murineshiftwork.logic.config.ini import deep_merge

    defaults = {"record_video": False, "laser_power": None}
    protocol = {"record_video": True, "laser_power": 0.8}
    result = deep_merge(defaults, protocol)
    assert result["record_video"] is True
    assert result["laser_power"] == pytest.approx(0.8)


def test_protocol_merge_null_laser_power_survives():
    from murineshiftwork.logic.config.ini import deep_merge

    defaults = {"laser_power": None, "pulse_duration": 0.001}
    protocol = {"pulse_duration": 0.005}
    result = deep_merge(defaults, protocol)
    assert result["laser_power"] is None


def test_popping_protocol_params_leaves_stim_params():
    from murineshiftwork.logic.config.ini import deep_merge

    defaults = {
        "n_trials": 50,
        "iti": 1.0,
        "record_video": False,
        "pulse_duration": 0.001,
        "pulse_frequency": 40,
    }
    protocol = {"pulse_duration": 0.005}
    params = dict(deep_merge(defaults, protocol))
    n_trials = params.pop("n_trials")
    iti = params.pop("iti")
    record_video = params.pop("record_video")
    assert n_trials == 50
    assert iti == pytest.approx(1.0)
    assert record_video is False
    assert "pulse_duration" in params
    assert "pulse_frequency" in params

"""Tests for config_io: load/save SetupConfig, SubjectConfig, update_valve_calibration."""
import pytest
import yaml
from pathlib import Path

from murineshiftwork.logic.config import SubjectConfig, SetupConfig, ValveCalibration
from murineshiftwork.logic.config import (
    load_setup_config,
    load_subject_config,
    save_subject_task_stage_position,
    update_valve_calibration,
)


POINTS_VALID = [
    [0.010, 0.675], [0.028, 2.075], [0.046, 4.15], [0.064, 6.525], [0.082, 9.05]
]


# ---------------------------------------------------------------------------
# load_setup_config

def test_load_setup_config_missing_file(tmp_path):
    result = load_setup_config(tmp_path, "nonexistent_setup")
    assert result is None


def test_load_setup_config_unknown_name(tmp_path):
    result = load_setup_config(tmp_path, "unknown_setup")
    assert result is None


def test_load_setup_config_valid(tmp_path):
    (tmp_path / "setups").mkdir()
    data = {
        "name": "test_setup",
        "devices": {
            "bpod": {"type": "bpod", "port_by_path": "test-path"}
        },
        "calibrations": {"bpod_valve": {}},
    }
    (tmp_path / "setups" / "test_setup.yaml").write_text(yaml.dump(data))
    cfg = load_setup_config(tmp_path, "test_setup")
    assert cfg is not None
    assert cfg.name == "test_setup"
    assert "bpod" in cfg.devices


def test_load_setup_config_with_calibration(tmp_path):
    (tmp_path / "setups").mkdir()
    data = {
        "name": "test_setup",
        "devices": {},
        "calibrations": {
            "bpod_valve": {
                "1": {"updated": "2025-08-07T10:00:00", "points": POINTS_VALID}
            }
        },
    }
    (tmp_path / "setups" / "test_setup.yaml").write_text(yaml.dump(data))
    cfg = load_setup_config(tmp_path, "test_setup")
    vc = cfg.calibrations.bpod_valve["1"]
    assert len(vc.points) == 5
    assert vc.ul_for_s(0.046) > 3.0


# ---------------------------------------------------------------------------
# load_subject_config

def test_load_subject_config_missing(tmp_path):
    result = load_subject_config(tmp_path, "s001_tabfixed_m1099615")
    assert result is None


def test_load_subject_config_test_subject_skipped(tmp_path):
    (tmp_path / "subjects").mkdir()
    result = load_subject_config(tmp_path, "_test_subject")
    assert result is None


def test_load_subject_config_valid(tmp_path):
    (tmp_path / "subjects").mkdir()
    data = {
        "name": "s001_tabfixed_m1099615",
        "project": "sleep_lhb",
        "task_overrides": {"_test_flush_water": {"VALVE_OPENING_TIME_MS": 70}},
    }
    (tmp_path / "subjects" / "s001_tabfixed_m1099615.yaml").write_text(yaml.dump(data))
    cfg = load_subject_config(tmp_path, "s001_tabfixed_m1099615")
    assert cfg is not None
    assert cfg.name == "s001_tabfixed_m1099615"
    assert cfg.task_overrides["_test_flush_water"]["VALVE_OPENING_TIME_MS"] == 70


# ---------------------------------------------------------------------------
# update_valve_calibration

def test_update_valve_calibration_no_file_raises(tmp_path):
    vc = ValveCalibration(updated="2025-01-01T00:00:00", points=POINTS_VALID)
    with pytest.raises(FileNotFoundError):
        update_valve_calibration(tmp_path, "missing_setup", 1, vc)


def test_update_valve_calibration_writes(tmp_path):
    (tmp_path / "setups").mkdir()
    path = tmp_path / "setups" / "test_setup.yaml"
    path.write_text(yaml.dump({"name": "test_setup", "devices": {}, "calibrations": {"bpod_valve": {}}}))

    vc = ValveCalibration(updated="2025-08-07T10:00:00", points=POINTS_VALID)
    written = update_valve_calibration(tmp_path, "test_setup", 1, vc)
    assert written is True

    with open(path) as f:
        raw = yaml.safe_load(f)
    assert "1" in raw["calibrations"]["bpod_valve"]
    assert raw["calibrations"]["bpod_valve"]["1"]["updated"] == "2025-08-07T10:00:00"


def test_update_valve_calibration_invalid_rejected(tmp_path):
    (tmp_path / "setups").mkdir()
    path = tmp_path / "setups" / "test_setup.yaml"
    path.write_text(yaml.dump({"name": "test_setup", "devices": {}, "calibrations": {"bpod_valve": {}}}))

    bad_points = [[10.0, 0.5], [20.0, 1.0]]  # only 2 points — invalid
    vc = ValveCalibration(updated="2025-08-07T10:00:00", points=bad_points)
    written = update_valve_calibration(tmp_path, "test_setup", 1, vc)
    assert written is False


def test_update_valve_calibration_force_overwrites(tmp_path):
    (tmp_path / "setups").mkdir()
    path = tmp_path / "setups" / "test_setup.yaml"
    path.write_text(yaml.dump({"name": "test_setup", "devices": {}, "calibrations": {"bpod_valve": {}}}))

    bad_points = [[10.0, 0.5], [20.0, 1.0]]  # invalid
    vc = ValveCalibration(updated="2025-08-07T10:00:00", points=bad_points)
    written = update_valve_calibration(tmp_path, "test_setup", 1, vc, force=True)
    assert written is True


def test_update_valve_calibration_preserves_other_fields(tmp_path):
    (tmp_path / "setups").mkdir()
    path = tmp_path / "setups" / "test_setup.yaml"
    existing = {
        "name": "test_setup",
        "devices": {"bpod": {"type": "bpod", "port_by_path": "some-path"}},
        "calibrations": {
            "bpod_valve": {
                "3": {"updated": "2024-01-01T00:00:00", "points": POINTS_VALID}
            }
        },
    }
    path.write_text(yaml.dump(existing))

    vc = ValveCalibration(updated="2025-08-07T10:00:00", points=POINTS_VALID)
    update_valve_calibration(tmp_path, "test_setup", 1, vc)

    with open(path) as f:
        raw = yaml.safe_load(f)
    # Existing valve 3 and bpod device must be preserved
    assert "3" in raw["calibrations"]["bpod_valve"]
    assert "bpod" in raw["devices"]


# ---------------------------------------------------------------------------
# save_subject_task_stage_position

def test_save_subject_task_stage_position_creates_file(tmp_path):
    save_subject_task_stage_position(
        tmp_path, "t001", "probabilistic_switching_fixedsubjects", "mouse_t001"
    )
    path = tmp_path / "subjects" / "t001.yaml"
    assert path.exists()

    with open(path) as f:
        raw = yaml.safe_load(f)
    overrides = raw["task_overrides"]["probabilistic_switching_fixedsubjects"]
    assert overrides["stage_position"] == "mouse_t001"


def test_save_subject_task_stage_position_merge_does_not_overwrite(tmp_path):
    # First call
    save_subject_task_stage_position(
        tmp_path, "t001", "probabilistic_switching_fixedsubjects", "mouse_t001"
    )
    # Second call with a different task — must not overwrite first entry
    save_subject_task_stage_position(
        tmp_path, "t001", "sequence", "mouse_t001_seq"
    )

    path = tmp_path / "subjects" / "t001.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    assert raw["task_overrides"]["probabilistic_switching_fixedsubjects"]["stage_position"] == "mouse_t001"
    assert raw["task_overrides"]["sequence"]["stage_position"] == "mouse_t001_seq"


def test_save_subject_task_stage_position_overwrites_position_in_same_task(tmp_path):
    save_subject_task_stage_position(tmp_path, "t001", "task_a", "old_pos")
    save_subject_task_stage_position(tmp_path, "t001", "task_a", "new_pos")

    path = tmp_path / "subjects" / "t001.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)
    assert raw["task_overrides"]["task_a"]["stage_position"] == "new_pos"


def test_save_subject_task_stage_position_preserves_other_task_override_keys(tmp_path):
    (tmp_path / "subjects").mkdir()
    path = tmp_path / "subjects" / "t001.yaml"
    existing = {
        "name": "t001",
        "task_overrides": {
            "task_a": {"VALVE_OPENING_TIME_MS": 70, "stage_position": "old_pos"}
        },
    }
    path.write_text(yaml.dump(existing))

    save_subject_task_stage_position(tmp_path, "t001", "task_a", "new_pos")

    with open(path) as f:
        raw = yaml.safe_load(f)
    # stage_position updated, other key preserved
    assert raw["task_overrides"]["task_a"]["stage_position"] == "new_pos"
    assert raw["task_overrides"]["task_a"]["VALVE_OPENING_TIME_MS"] == 70

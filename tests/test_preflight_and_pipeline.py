"""Tests for pre-flight hardware check, data_dir resolution, and settings pipeline."""

import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# resolve_data_dir


def test_resolve_data_dir_historical_default(tmp_path, monkeypatch):
    monkeypatch.delenv("MSW_DATA_DIR", raising=False)
    from murineshiftwork.logic import machine_config as mc

    # Patch _HISTORICAL_DATA_DEFAULT to tmp_path (which exists)
    monkeypatch.setattr(mc, "_HISTORICAL_DATA_DEFAULT", tmp_path)
    monkeypatch.setattr(mc, "_MACHINE_CONFIG_FILE", tmp_path / "msw_machine.yaml")
    result = mc.resolve_data_dir()
    assert result == str(tmp_path)


def test_resolve_data_dir_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("MSW_DATA_DIR", str(tmp_path))
    from murineshiftwork.logic.machine_config import resolve_data_dir

    assert resolve_data_dir() == str(tmp_path)


def test_resolve_data_dir_cli_override(tmp_path, monkeypatch):
    monkeypatch.delenv("MSW_DATA_DIR", raising=False)
    from murineshiftwork.logic.machine_config import resolve_data_dir

    assert resolve_data_dir(cli_override=str(tmp_path)) == str(tmp_path)


def test_resolve_data_dir_machine_config(tmp_path, monkeypatch):
    monkeypatch.delenv("MSW_DATA_DIR", raising=False)
    from murineshiftwork.logic import machine_config as mc

    cfg_file = tmp_path / "msw_machine.yaml"
    cfg_file.write_text(yaml.dump({"data_dir": str(tmp_path / "mydata")}))
    monkeypatch.setattr(mc, "_MACHINE_CONFIG_FILE", cfg_file)
    # Make historical default not exist so machine config wins
    monkeypatch.setattr(mc, "_HISTORICAL_DATA_DEFAULT", tmp_path / "nonexistent")
    result = mc.resolve_data_dir()
    assert result == str(tmp_path / "mydata")


# ---------------------------------------------------------------------------
# task discovery without __init__.py


def test_list_available_tasks_nonempty():
    from murineshiftwork.cli.tasks import list_available_tasks

    # Public msw-tasks-core tasks (the `tasks` extra); lab tasks are tested in
    # msw-tasks-lab.
    tasks = list_available_tasks()
    assert len(tasks) >= 5
    assert "_test_flush_valves" in tasks
    assert "_calibration_liquid_dynamic" in tasks


def test_find_task_by_name():
    from murineshiftwork.cli.tasks import find_task_by_name, list_available_tasks

    assert find_task_by_name("flush") == "_test_flush_valves"
    assert find_task_by_name("_calibration_sound") in list_available_tasks()
    assert find_task_by_name("nonexistent_xyz_task") is None


def test_get_task_dir_returns_path():
    from murineshiftwork.cli.evaluate import get_task_dir

    d = get_task_dir("_test_flush_valves")
    assert d != ""
    assert Path(d).is_dir()


# ---------------------------------------------------------------------------
# settings pipeline: calibration files in patched settings


def _write_subject_yaml(path, subject_name, task_overrides=None):
    data = {
        "name": subject_name,
        "registered": "2026-01-01T00:00:00",
        "project": "",
        "experiment": "",
        "comment": "",
        "aliases": [],
        "task_overrides": task_overrides or {},
    }
    p = path / "subjects" / f"{subject_name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        yaml.dump(data, f)
    return p


def _write_setup_yaml(path, setup_name):
    data = {
        "name": setup_name,
        "devices": {"bpod": {"type": "bpod", "port_by_path": "pci-test:1.0"}},
        "calibrations": {"bpod_valve": {}},
    }
    p = path / "setups" / f"{setup_name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        yaml.dump(data, f)
    return p


def test_calibration_files_in_patched_settings(tmp_path):
    """calibration_file_liquid injected into settings.task.patched from CLI args."""
    from murineshiftwork.cli.evaluate import evaluate_args

    _write_subject_yaml(tmp_path, "subj001")
    _write_setup_yaml(tmp_path, "setup-test")
    fake_cal = tmp_path / "cal.csv"
    fake_cal.touch()

    args = dict(
        command="run",
        subject="subj001",
        task="_test_flush_valves",
        task_dir="",
        config_dir=str(tmp_path),
        config_file_subjects="subject.settings",
        config_file_task="task.settings",
        config_file_camera="camera.rcc.config",
        calibration_file_liquid=str(fake_cal),
        calibration_file_sound="calibration.sound.default.csv",
        calibration_file_stage=str(tmp_path / "stage.yaml"),
        serial_port_bpod="/dev/ttyACM0",
        serial_port_pulsepal="/dev/ttyACM1",
        serial_port_scale="/dev/ttyACM2",
        serial_port_stage="/dev/ttyUSB0",
        out_path=str(tmp_path / "data"),
        linked_to="",
        setup="setup-test",
        experiment="test",
        researcher="test",
        metadata_list=None,
        log_level="INFO",
        log_file=str(tmp_path / "test.log"),
        debug=True,  # skip preflight
        task_settings_overrides=[],
    )
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched.get("calibration_file_liquid") == str(fake_cal)
    assert "serial_port_stage" in patched


def test_cli_ts_overrides_calibration_file(tmp_path):
    """CLI -ts KEY=VALUE overrides the injected calibration file path."""
    from murineshiftwork.cli.evaluate import evaluate_args

    _write_subject_yaml(tmp_path, "subj001")
    _write_setup_yaml(tmp_path, "setup-test")
    fake_cal_default = tmp_path / "default.csv"
    fake_cal_default.touch()
    fake_cal_override = tmp_path / "override.csv"
    fake_cal_override.touch()

    args = dict(
        command="run",
        subject="subj001",
        task="_test_flush_valves",
        task_dir="",
        config_dir=str(tmp_path),
        config_file_subjects="subject.settings",
        config_file_task="task.settings",
        config_file_camera="camera.rcc.config",
        calibration_file_liquid=str(fake_cal_default),
        calibration_file_sound="calibration.sound.default.csv",
        calibration_file_stage=str(tmp_path / "stage.yaml"),
        serial_port_bpod="/dev/ttyACM0",
        serial_port_pulsepal="/dev/ttyACM1",
        serial_port_scale="/dev/ttyACM2",
        serial_port_stage="/dev/ttyUSB0",
        out_path=str(tmp_path / "data"),
        linked_to="",
        setup="setup-test",
        experiment="test",
        researcher="test",
        metadata_list=None,
        log_level="INFO",
        log_file=str(tmp_path / "test.log"),
        debug=True,
        task_settings_overrides=[f"calibration_file_liquid={fake_cal_override}"],
    )
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched["calibration_file_liquid"] == str(fake_cal_override)


def test_subject_task_overrides_applied(tmp_path):
    """SubjectConfig.task_overrides patches N_FLUSH_CYCLES."""
    from murineshiftwork.cli.evaluate import evaluate_args

    _write_subject_yaml(
        tmp_path,
        "subj001",
        task_overrides={"_test_flush_valves": {"N_FLUSH_CYCLES": 7}},
    )
    _write_setup_yaml(tmp_path, "setup-test")

    args = dict(
        command="run",
        subject="subj001",
        task="_test_flush_valves",
        task_dir="",
        config_dir=str(tmp_path),
        config_file_subjects="subject.settings",
        config_file_task="task.settings",
        config_file_camera="camera.rcc.config",
        calibration_file_liquid="cal.csv",
        calibration_file_sound="cal_sound.csv",
        calibration_file_stage="stage.yaml",
        serial_port_bpod="/dev/ttyACM0",
        serial_port_pulsepal="/dev/ttyACM1",
        serial_port_scale="/dev/ttyACM2",
        serial_port_stage="/dev/ttyUSB0",
        out_path=str(tmp_path / "data"),
        linked_to="",
        setup="setup-test",
        experiment="test",
        researcher="test",
        metadata_list=None,
        log_level="INFO",
        log_file=str(tmp_path / "test.log"),
        debug=True,
        task_settings_overrides=[],
    )
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched.get("N_FLUSH_CYCLES") == 7


# ---------------------------------------------------------------------------
# pre-flight check


def test_preflight_passes_for_debug(tmp_path):
    """Preflight is bypassed in debug mode."""
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    # Should not raise even with non-existent ports
    _preflight_hardware_check(
        {
            "debug": True,
            "out_path": str(tmp_path),
            "serial_port_bpod": "/dev/nonexistent",
            "settings.task.patched": {},
            "setup_config": None,
        }
    )


def test_preflight_passes_for_test_subject(tmp_path):
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    _preflight_hardware_check(
        {
            "debug": False,
            "subject": "_test_subject",
            "out_path": str(tmp_path),
            "serial_port_bpod": "/dev/nonexistent",
            "settings.task.patched": {},
            "setup_config": None,
        }
    )


def test_preflight_fails_on_bad_bpod_port(tmp_path):
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    with pytest.raises(RuntimeError, match="Bpod serial port not accessible"):
        _preflight_hardware_check(
            {
                "debug": False,
                "subject": "real_subject",
                "out_path": str(tmp_path),
                "serial_port_bpod": "/dev/tty_nonexistent_bpod_xyz",
                "settings.task.patched": {},
                "setup_config": None,
            }
        )


def test_preflight_fails_on_missing_camera_config(tmp_path):
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    with pytest.raises(RuntimeError, match="Camera config not found"):
        _preflight_hardware_check(
            {
                "debug": False,
                "subject": "real_subject",
                "out_path": str(tmp_path),
                "serial_port_bpod": "",  # skip bpod check
                "config_file_camera": "/nonexistent/camera.yaml",
                "settings.task.patched": {"record_video": True},
                "setup_config": None,
            }
        )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="no portable always-unwritable path on Windows; writability logic is OS-agnostic",
)
def test_preflight_fails_on_nonwritable_output():
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    with pytest.raises(RuntimeError, match="(not writable|Cannot create)"):
        _preflight_hardware_check(
            {
                "debug": False,
                "subject": "real_subject",
                "out_path": "/root/cannot_write_here_ever",
                "serial_port_bpod": "",
                "settings.task.patched": {},
                "setup_config": None,
            }
        )


def test_preflight_collects_multiple_errors(tmp_path):
    """All failing checks are reported together."""
    from murineshiftwork.cli.preflight import (
        preflight_hardware_check as _preflight_hardware_check,
    )

    with pytest.raises(RuntimeError) as exc_info:
        _preflight_hardware_check(
            {
                "debug": False,
                "subject": "real_subject",
                "out_path": str(tmp_path),
                "serial_port_bpod": "/dev/tty_bad_bpod",
                "config_file_camera": "/nonexistent/cam.yaml",
                "settings.task.patched": {"record_video": True},
                "setup_config": None,
            }
        )
    msg = str(exc_info.value)
    assert "Bpod" in msg
    assert "Camera" in msg


# ---------------------------------------------------------------------------
# importlib-based task import


def test_init_task_uses_importlib():
    """get_task_dir uses importlib, not exec."""
    from murineshiftwork.cli.evaluate import get_task_dir

    d = get_task_dir("_test_flush_valves")
    assert Path(d).exists()
    # Must not have injected anything into globals via exec
    assert "ThisTask" not in globals()

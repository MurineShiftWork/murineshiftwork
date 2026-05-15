"""Tests for CLI evaluate layer: settings patching, subject lookup, _parse_key_value_list."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from murineshiftwork.cli.evaluate import _parse_key_value_list


# ---------------------------------------------------------------------------
# _parse_key_value_list

def test_parse_kv_basic():
    result = _parse_key_value_list(["VALVE_OPENING_TIME_MS=80"])
    assert result == {"VALVE_OPENING_TIME_MS": 80}


def test_parse_kv_float():
    result = _parse_key_value_list(["INTER_FLUSH_INTERVAL_S=1.5"])
    assert result == {"INTER_FLUSH_INTERVAL_S": 1.5}


def test_parse_kv_list():
    result = _parse_key_value_list(["VALVE_NUMBERS=[1,3]"])
    assert result == {"VALVE_NUMBERS": [1, 3]}


def test_parse_kv_string_fallback():
    result = _parse_key_value_list(["NAME=hello_world"])
    assert result == {"NAME": "hello_world"}


def test_parse_kv_multiple():
    result = _parse_key_value_list(["A=1", "B=2.5", "C=some_string"])
    assert result["A"] == 1
    assert result["B"] == 2.5
    assert result["C"] == "some_string"


def test_parse_kv_empty_list():
    assert _parse_key_value_list([]) == {}


def test_parse_kv_no_equals_skipped():
    result = _parse_key_value_list(["NOVALUE"])
    assert result == {}


# ---------------------------------------------------------------------------
# Helpers

def _base_args(tmp_path, subject, task="_test_flush_water", **overrides):
    """Return a minimal valid args_dict for evaluate_args testing."""
    base = {
        "command": "run",
        "subject": subject,
        "task": task,
        "debug": False,
        "log_level": "INFO",
        "log_file": str(tmp_path / "test.log"),
        "config_dir": str(tmp_path),
        "config_file_subjects": "",
        "config_file_task": "",
        "config_file_camera": "",
        "calibration_file_water": "",
        "calibration_file_sound": "",
        "calibration_file_stage": str(tmp_path / "nonexistent.yaml"),
        "serial_port_bpod": "/dev/ttyACM0",
        "task_settings_overrides": [],
        "metadata_list": None,
        "researcher": "unknown_researcher",
        "setup": "unknown_setup",
        "experiment": "unknown_experiment",
        "out_path": str(tmp_path / "data"),
        "is_child_session_to": "",
        "serial_port_pulsepal": "/dev/ttyACM1",
        "serial_port_scale": "/dev/ttyACM2",
        "serial_port_stage": "/dev/ttyUSB0",
        "host_name": "test",
        "host_ip": "127.0.0.1",
        "original": {},
        "settings.stage": {},
        "task_dir": "",
    }
    base.update(overrides)
    return base


def _write_subject_yaml(tmp_path, name, **fields):
    (tmp_path / "subjects").mkdir(exist_ok=True)
    data = {"name": name, **fields}
    (tmp_path / "subjects" / f"{name}.yaml").write_text(yaml.dump(data))


# ---------------------------------------------------------------------------
# Settings patching: SubjectConfig.task_overrides applied

def test_subject_yaml_task_overrides_applied(tmp_path):
    """SubjectConfig.task_overrides are merged into settings.task.patched."""
    from murineshiftwork.cli.evaluate import evaluate_args
    subject = "s082_tabfixed_m1000001"
    _write_subject_yaml(
        tmp_path, subject,
        task_overrides={"_test_flush_water": {"VALVE_OPENING_TIME_MS": 77}},
    )
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 77


def test_cli_task_settings_override_highest_priority(tmp_path):
    """CLI --task-settings KEY=VALUE beats subject YAML task_overrides."""
    from murineshiftwork.cli.evaluate import evaluate_args
    subject = "s082_tabfixed_m1000002"
    _write_subject_yaml(
        tmp_path, subject,
        task_overrides={"_test_flush_water": {"VALVE_OPENING_TIME_MS": 77}},
    )
    args = _base_args(tmp_path, subject,
                      task_settings_overrides=["VALVE_OPENING_TIME_MS=90"])
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 90


def test_unknown_subject_raises_without_yaml(tmp_path):
    """Unknown subject not in INI and no YAML raises ValueError."""
    from murineshiftwork.cli.evaluate import evaluate_args
    (tmp_path / "subjects").mkdir()
    args = _base_args(tmp_path, "s999_unknown_m9999999")
    with pytest.raises(ValueError, match="Unknown subject"):
        evaluate_args(args_dict=args)


def test_yaml_subject_accepted_without_ini(tmp_path):
    """A subject with only a YAML config (not in INI) is accepted."""
    from murineshiftwork.cli.evaluate import evaluate_args
    subject = "s082_tabfixed_m1000003"
    _write_subject_yaml(tmp_path, subject)
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    assert "exit_flag" not in result
    assert result["execution_config"].subject.name == subject

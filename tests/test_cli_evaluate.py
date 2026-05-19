"""Tests for CLI evaluate layer: settings patching, subject lookup, parse_key_value_list."""

import pytest
import yaml

from murineshiftwork.logic.task_settings import parse_key_value_list

# ---------------------------------------------------------------------------
# parse_key_value_list


def test_parse_kv_basic():
    result = parse_key_value_list(["VALVE_OPENING_TIME_MS=80"])
    assert result == {"VALVE_OPENING_TIME_MS": 80}


def test_parse_kv_float():
    result = parse_key_value_list(["INTER_FLUSH_INTERVAL_S=1.5"])
    assert result == {"INTER_FLUSH_INTERVAL_S": 1.5}


def test_parse_kv_list():
    result = parse_key_value_list(["VALVE_NUMBERS=[1,3]"])
    assert result == {"VALVE_NUMBERS": [1, 3]}


def test_parse_kv_string_fallback():
    result = parse_key_value_list(["NAME=hello_world"])
    assert result == {"NAME": "hello_world"}


def test_parse_kv_multiple():
    result = parse_key_value_list(["A=1", "B=2.5", "C=some_string"])
    assert result["A"] == 1
    assert result["B"] == 2.5
    assert result["C"] == "some_string"


def test_parse_kv_empty_list():
    assert parse_key_value_list([]) == {}


def test_parse_kv_no_equals_skipped():
    result = parse_key_value_list(["NOVALUE"])
    assert result == {}


# ---------------------------------------------------------------------------
# Helpers


def _base_args(tmp_path, subject, task="_test_flush_water", **overrides):
    """Return a minimal valid args_dict for evaluate_args testing."""
    base = {
        "command": "run",
        "simulate": True,  # skip hardware preflight in CI (no /dev/ttyACM0)
        "subject": subject,
        "task": task,
        "debug": False,
        "log_level": "INFO",
        "log_file": str(tmp_path / "test.log"),
        "config_dir": str(tmp_path),
        "config_file_subjects": "",
        "config_file_task": "task.yaml",
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
        tmp_path,
        subject,
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
        tmp_path,
        subject,
        task_overrides={"_test_flush_water": {"VALVE_OPENING_TIME_MS": 77}},
    )
    args = _base_args(
        tmp_path, subject, task_settings_overrides=["VALVE_OPENING_TIME_MS=90"]
    )
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


# ---------------------------------------------------------------------------
# Config-dir task overlay


def _write_task_overlay(tmp_path, task, content: dict):
    overlay_dir = tmp_path / "tasks" / task
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "task.yaml").write_text(yaml.dump({"default": content}))


def test_task_overlay_overrides_bundled_default(tmp_path):
    """config_dir/tasks/<task>/task.yaml value wins over bundled task.yaml."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000001"
    _write_subject_yaml(tmp_path, subject)
    _write_task_overlay(tmp_path, "_test_flush_water", {"VALVE_OPENING_TIME_MS": 123.0})
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 123.0


def test_task_overlay_preserves_unmentioned_bundled_keys(tmp_path):
    """Overlay only replaces what it declares; bundled keys absent from overlay survive."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000002"
    _write_subject_yaml(tmp_path, subject)
    # Override only VALVE_OPENING_TIME_MS; N_FLUSH_CYCLES should come from bundled defaults
    _write_task_overlay(tmp_path, "_test_flush_water", {"VALVE_OPENING_TIME_MS": 77.0})
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched["VALVE_OPENING_TIME_MS"] == 77.0
    assert "N_FLUSH_CYCLES" in patched  # from bundled default, not clobbered


def test_task_overlay_absent_uses_bundled_only(tmp_path):
    """When no overlay file exists the bundled default is used unchanged."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000003"
    _write_subject_yaml(tmp_path, subject)
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    # Bundled _test_flush_water default is 50.0
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 50.0
    assert result["config_file_task_overlay"] == ""


def test_cli_override_beats_task_overlay(tmp_path):
    """CLI --task-settings-overrides wins over config-dir overlay (highest priority)."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000004"
    _write_subject_yaml(tmp_path, subject)
    _write_task_overlay(tmp_path, "_test_flush_water", {"VALVE_OPENING_TIME_MS": 123.0})
    args = _base_args(
        tmp_path, subject, task_settings_overrides=["VALVE_OPENING_TIME_MS=200"]
    )
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 200


def test_task_overlay_deep_merges_nested_keys(tmp_path):
    """Overlay merges nested dicts rather than replacing the whole nested block."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000005"
    _write_subject_yaml(tmp_path, subject)
    # _test_flush_water has no nested keys; use a contrived overlay with a nested dict
    _write_task_overlay(
        tmp_path,
        "_test_flush_water",
        {"hardware": {"port": "/dev/ttyACM9"}, "VALVE_OPENING_TIME_MS": 55.0},
    )
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched["hardware"]["port"] == "/dev/ttyACM9"
    assert patched["VALVE_OPENING_TIME_MS"] == 55.0


# ---------------------------------------------------------------------------
# Sticky task_mode from subject YAML


def _write_task_overlay_with_mode(tmp_path, task, mode_name, mode_params):
    """Write overlay task.yaml with both default: and mode: sections."""
    overlay_dir = tmp_path / "tasks" / task
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "task.yaml").write_text(
        yaml.dump({"default": {}, "mode": {mode_name: mode_params}})
    )


def test_sticky_task_mode_from_subject_yaml_applied(tmp_path):
    """task_mode in subject YAML task_overrides is applied like --task-mode."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m3000001"
    _write_subject_yaml(
        tmp_path,
        subject,
        task_overrides={"_test_flush_water": {"task_mode": "low_volume"}},
    )
    _write_task_overlay_with_mode(
        tmp_path, "_test_flush_water", "low_volume", {"VALVE_OPENING_TIME_MS": 25.0}
    )
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 25.0


def test_cli_task_mode_beats_sticky_subject_yaml_mode(tmp_path):
    """CLI --task-mode overrides task_mode stored in subject YAML."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m3000002"
    _write_subject_yaml(
        tmp_path,
        subject,
        task_overrides={"_test_flush_water": {"task_mode": "low_volume"}},
    )
    _write_task_overlay_with_mode(
        tmp_path,
        "_test_flush_water",
        "low_volume",
        {"VALVE_OPENING_TIME_MS": 25.0},
    )
    # Add a second mode to select via CLI
    overlay_dir = tmp_path / "tasks" / "_test_flush_water"
    (overlay_dir / "task.yaml").write_text(
        yaml.dump(
            {
                "default": {},
                "mode": {
                    "low_volume": {"VALVE_OPENING_TIME_MS": 25.0},
                    "high_volume": {"VALVE_OPENING_TIME_MS": 99.0},
                },
            }
        )
    )
    args = _base_args(tmp_path, subject, task_mode="high_volume")
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 99.0


def test_subject_yaml_overrides_stack_on_top_of_sticky_mode(tmp_path):
    """Non-mode keys in subject YAML override the mode's params."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m3000003"
    _write_subject_yaml(
        tmp_path,
        subject,
        task_overrides={
            "_test_flush_water": {
                "task_mode": "low_volume",
                "N_FLUSH_CYCLES": 7,  # subject key on top of mode
            }
        },
    )
    _write_task_overlay_with_mode(
        tmp_path, "_test_flush_water", "low_volume", {"VALVE_OPENING_TIME_MS": 25.0}
    )
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    patched = result["settings.task.patched"]
    assert patched["VALVE_OPENING_TIME_MS"] == 25.0  # from mode
    assert patched["N_FLUSH_CYCLES"] == 7  # subject key on top of mode


def test_full_priority_chain_order(tmp_path):
    """Verify full priority chain: bundled < overlay < subject_overrides < CLI."""
    from murineshiftwork.cli.evaluate import evaluate_args

    subject = "s082_tabfixed_m2000006"
    # bundled default: VALVE_OPENING_TIME_MS = 50
    # overlay:         VALVE_OPENING_TIME_MS = 100
    # subject yaml:    VALVE_OPENING_TIME_MS = 150
    # CLI:             VALVE_OPENING_TIME_MS = 200
    _write_subject_yaml(
        tmp_path,
        subject,
        task_overrides={"_test_flush_water": {"VALVE_OPENING_TIME_MS": 150.0}},
    )
    _write_task_overlay(tmp_path, "_test_flush_water", {"VALVE_OPENING_TIME_MS": 100.0})

    # Without CLI override: subject yaml (150) wins
    args = _base_args(tmp_path, subject)
    result = evaluate_args(args_dict=args)
    assert result["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 150.0

    # With CLI override: CLI (200) wins
    args_cli = _base_args(
        tmp_path, subject, task_settings_overrides=["VALVE_OPENING_TIME_MS=200"]
    )
    result_cli = evaluate_args(args_dict=args_cli)
    assert result_cli["settings.task.patched"]["VALVE_OPENING_TIME_MS"] == 200
    assert result["execution_config"].subject.name == subject

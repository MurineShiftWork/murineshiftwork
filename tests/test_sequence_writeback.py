"""Integration test: sequence task save_session_end() writes start_level to subject YAML."""

import pytest
import yaml

pytest.importorskip("ttl_barcoder")
# sequence is a lab task (msw-tasks-lab, private); skip when absent.
pytest.importorskip("murineshiftwork.tasks.sequence")


def _make_subject_yaml(tmp_path, subject="mouse001"):
    (tmp_path / "subjects").mkdir(exist_ok=True)
    path = tmp_path / "subjects" / f"{subject}.yaml"
    path.write_text(yaml.dump({"name": subject, "task_overrides": {}}))
    return path


def _make_task_control(subject, config_dir, current_level=7, session_start_level=5):
    """Construct a TaskControl without calling __init__ (avoids Bpod + full settings)."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    tc = object.__new__(TaskControl)
    tc.task_settings = {"subject": subject, "config_dir": str(config_dir)}
    tc.current_level = current_level
    tc._session_start_level = session_start_level
    tc._session_task_trials = 0
    tc._session_no_response_count = 0
    tc._session_reward_count = 0
    tc._session_liquid_ul = 0.0
    tc.trial_index = 42
    return tc


def test_save_session_end_writes_start_level_to_subject_yaml(tmp_path, monkeypatch):
    """save_session_end() persists current_level as start_level in subject YAML."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    # Patch out the JSON-store methods (they write to ~/.murineshiftwork/sequence/)
    monkeypatch.setattr(TaskControl, "_fetch_subject_state", lambda self, s: {})
    monkeypatch.setattr(TaskControl, "_push_subject_state", lambda self, s, d: None)
    monkeypatch.setattr(TaskControl, "_register_subject", lambda self, s: None)

    path = _make_subject_yaml(tmp_path)
    tc = _make_task_control("mouse001", tmp_path, current_level=7)
    tc.save_session_end()

    raw = yaml.safe_load(path.read_text())
    assert raw["task_overrides"]["sequence"]["start_level"] == 7


def test_save_session_end_updates_existing_level(tmp_path, monkeypatch):
    """Calling save_session_end() twice updates the level each time."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    monkeypatch.setattr(TaskControl, "_fetch_subject_state", lambda self, s: {})
    monkeypatch.setattr(TaskControl, "_push_subject_state", lambda self, s, d: None)
    monkeypatch.setattr(TaskControl, "_register_subject", lambda self, s: None)

    path = _make_subject_yaml(tmp_path)
    tc = _make_task_control("mouse001", tmp_path, current_level=4)
    tc.save_session_end()

    tc.current_level = 5
    tc.save_session_end()

    raw = yaml.safe_load(path.read_text())
    assert raw["task_overrides"]["sequence"]["start_level"] == 5


def test_save_session_end_preserves_other_task_overrides(tmp_path, monkeypatch):
    """save_session_end() does not touch task_overrides for other tasks."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    monkeypatch.setattr(TaskControl, "_fetch_subject_state", lambda self, s: {})
    monkeypatch.setattr(TaskControl, "_push_subject_state", lambda self, s, d: None)
    monkeypatch.setattr(TaskControl, "_register_subject", lambda self, s: None)

    (tmp_path / "subjects").mkdir()
    path = tmp_path / "subjects" / "mouse001.yaml"
    path.write_text(
        yaml.dump(
            {
                "name": "mouse001",
                "task_overrides": {
                    "probabilistic_switching": {"REWARD_VOLUME_UL": 4.0},
                },
            }
        )
    )

    tc = _make_task_control("mouse001", tmp_path, current_level=3)
    tc.save_session_end()

    raw = yaml.safe_load(path.read_text())
    assert raw["task_overrides"]["sequence"]["start_level"] == 3
    assert raw["task_overrides"]["probabilistic_switching"]["REWARD_VOLUME_UL"] == 4.0


def test_save_session_end_skips_test_subjects(tmp_path, monkeypatch):
    """save_session_end() does not write to subject YAML for _test_* subjects."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    monkeypatch.setattr(TaskControl, "_fetch_subject_state", lambda self, s: {})
    monkeypatch.setattr(TaskControl, "_push_subject_state", lambda self, s, d: None)
    monkeypatch.setattr(TaskControl, "_register_subject", lambda self, s: None)

    path = _make_subject_yaml(tmp_path, subject="_test_subject")
    tc = _make_task_control("_test_subject", tmp_path, current_level=9)
    tc.save_session_end()

    raw = yaml.safe_load(path.read_text())
    assert "sequence" not in raw.get("task_overrides", {})


def test_save_session_end_skips_when_no_config_dir(tmp_path, monkeypatch):
    """save_session_end() silently skips YAML writeback when config_dir is empty."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    monkeypatch.setattr(TaskControl, "_fetch_subject_state", lambda self, s: {})
    monkeypatch.setattr(TaskControl, "_push_subject_state", lambda self, s, d: None)
    monkeypatch.setattr(TaskControl, "_register_subject", lambda self, s: None)

    path = _make_subject_yaml(tmp_path)
    tc = _make_task_control("mouse001", config_dir="", current_level=5)
    tc.save_session_end()  # must not raise

    raw = yaml.safe_load(path.read_text())
    assert "sequence" not in raw.get("task_overrides", {})

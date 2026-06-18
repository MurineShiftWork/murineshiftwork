"""Tests for session YAML write safety.

Covers:
  _strip_unserializable : strips callables before yaml.safe_dump
  update_session_yaml   : writes safe YAML, merges with existing content

_PermissiveLoader tests (historical read tolerance) live in msw-io:
  msw-io/tests/test_readers_session.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# _strip_unserializable


def test_strip_removes_top_level_callable(tmp_path):
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"a": 1, "fn": lambda x: x, "b": "hello"}
    result = _strip_unserializable(d)
    assert "fn" not in result
    assert result["a"] == 1
    assert result["b"] == "hello"


def test_strip_removes_nested_callable():
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"outer": {"inner_fn": lambda: None, "val": 42}}
    result = _strip_unserializable(d)
    assert "inner_fn" not in result["outer"]
    assert result["outer"]["val"] == 42


def test_strip_removes_callable_in_list():
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"items": [1, lambda: None, 3]}
    result = _strip_unserializable(d)
    assert result["items"] == [1, 3]


def test_strip_preserves_none():
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"key": None}
    assert _strip_unserializable(d) == {"key": None}


def test_strip_preserves_all_scalar_types():
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"i": 1, "f": 3.14, "b": True, "s": "text", "n": None}
    assert _strip_unserializable(d) == d


def test_strip_preserves_nested_lists_and_dicts():
    from murineshiftwork.logic.task_process import _strip_unserializable

    d = {"a": [{"x": 1}, {"y": 2}]}
    assert _strip_unserializable(d) == d


def test_strip_empty_dict():
    from murineshiftwork.logic.task_process import _strip_unserializable

    assert _strip_unserializable({}) == {}


# ---------------------------------------------------------------------------
# update_session_yaml: write behaviour


def _session_base(tmp_path: Path) -> Path:
    d = tmp_path / "sub" / "sub__20260101_120000_000001__task"
    d.mkdir(parents=True)
    return d / "sub__20260101_120000_000001__task"


def test_update_session_yaml_creates_file(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(base, task_settings={"n_trials": 10})
    out = Path(str(base) + ".msw.session.yaml")
    assert out.exists()


def test_update_session_yaml_writes_msw_format_version(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(base, task_settings={"n_trials": 10})
    data = yaml.safe_load(Path(str(base) + ".msw.session.yaml").read_text())
    assert data["msw_format_version"] == 2


def test_update_session_yaml_strips_callable(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(
        base, task_settings={"n_trials": 5, "valve_s_for_ul": lambda v: v}
    )
    text = Path(str(base) + ".msw.session.yaml").read_text()
    assert "python/name" not in text
    assert "lambda" not in text
    data = yaml.safe_load(text)
    assert data["task_settings"]["n_trials"] == 5
    assert "valve_s_for_ul" not in data["task_settings"]


def test_update_session_yaml_output_is_safe_loadable(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(base, task_settings={"valve_s_for_ul": lambda v: v, "a": 1})
    text = Path(str(base) + ".msw.session.yaml").read_text()
    data = yaml.safe_load(text)
    assert isinstance(data, dict)


def test_update_session_yaml_merges_existing(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(base, process={"task": "seq"})
    update_session_yaml(base, task_settings={"n_trials": 3})
    data = yaml.safe_load(Path(str(base) + ".msw.session.yaml").read_text())
    assert data["process"]["task"] == "seq"
    assert data["task_settings"]["n_trials"] == 3


def test_update_session_yaml_overwrites_existing_key(tmp_path):
    from murineshiftwork.logic.task_process import update_session_yaml

    base = _session_base(tmp_path)
    update_session_yaml(base, task_settings={"n_trials": 3})
    update_session_yaml(base, task_settings={"n_trials": 99})
    data = yaml.safe_load(Path(str(base) + ".msw.session.yaml").read_text())
    assert data["task_settings"]["n_trials"] == 99

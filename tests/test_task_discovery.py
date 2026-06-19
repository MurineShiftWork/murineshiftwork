"""Tests for task discovery: filesystem scan + msw.tasks entry-point path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from murineshiftwork.cli.tasks import (
    find_task_by_name,
    list_available_tasks,
    load_task_module,
)

# ---------------------------------------------------------------------------
# Filesystem discovery


def test_filesystem_returns_known_bundled_tasks():
    # Use msw-tasks-core tasks (public, installed via the `tasks` extra) - lab
    # tasks (sequence/airpuff/optotagging) are tested in msw-tasks-lab.
    tasks = list_available_tasks()
    assert "_calibration_liquid_dynamic" in tasks
    assert "_calibration_liquid_static" in tasks
    assert "_calibration_sound_latency" in tasks


def test_filesystem_result_is_sorted():
    tasks = list_available_tasks()
    assert tasks == sorted(tasks)


def test_filesystem_detailed_returns_dict_of_paths():
    tasks = list_available_tasks(detailed=True)
    assert isinstance(tasks, dict)
    for path in tasks.values():
        assert isinstance(path, Path)
        assert path.is_dir()


def test_filesystem_includes_test_and_calibration_prefixed():
    tasks = list_available_tasks()
    assert any(t.startswith("_test_") for t in tasks)
    assert any(t.startswith("_calibration_") for t in tasks)


def test_filesystem_excludes_other_private_dirs():
    tasks = list_available_tasks()
    for name in tasks:
        assert (
            not name.startswith("_")
            or name.startswith("_test_")
            or name.startswith("_calibration_")
        )


def test_filesystem_task_dir_contains_expected_module():
    tasks = list_available_tasks(detailed=True)
    for name, path in tasks.items():
        assert (path / "task.py").exists(), f"{name}: expected task.py in {path}"


# ---------------------------------------------------------------------------
# Entry-point discovery


def _make_ep(name: str, value: str) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.value = value
    return ep


def test_external_task_added_via_entry_point():
    # Use a real importable module as the ep value so __file__ is not None.
    ep = _make_ep("ext_task", "murineshiftwork.cli.tasks")
    with patch("murineshiftwork.cli.tasks.entry_points", return_value=[ep]):
        tasks = list_available_tasks()
    assert "ext_task" in tasks


def test_external_task_path_is_dir_of_ep_module():
    ep = _make_ep("ext_task", "murineshiftwork.cli.tasks")
    with patch("murineshiftwork.cli.tasks.entry_points", return_value=[ep]):
        tasks = list_available_tasks(detailed=True)
    assert isinstance(tasks["ext_task"], Path)


def test_bundled_task_takes_precedence_over_entry_point():
    # Register a clashing bundled name as an entry point - bundled must win.
    ep = _make_ep("_calibration_liquid_dynamic", "murineshiftwork.cli.tasks")
    with (
        patch("murineshiftwork.cli.tasks.entry_points", return_value=[ep]),
        patch("murineshiftwork.cli.tasks.importlib.import_module") as mock_import,
    ):
        tasks = list_available_tasks(detailed=True)
    # import_module must NOT be called for the clashing name.
    mock_import.assert_not_called()
    # The path from filesystem (a real dir with task.py) is used.
    assert (tasks["_calibration_liquid_dynamic"] / "task.py").exists()


def test_failed_entry_point_load_is_silently_skipped():
    ep = _make_ep("broken_ext_task", "nonexistent.module.xyz")
    with patch("murineshiftwork.cli.tasks.entry_points", return_value=[ep]):
        tasks = list_available_tasks()
    assert "broken_ext_task" not in tasks


# ---------------------------------------------------------------------------
# find_task_by_name


def test_find_task_exact_match():
    assert (
        find_task_by_name("_calibration_sound_latency") == "_calibration_sound_latency"
    )


def test_find_task_partial_unique_match():
    result = find_task_by_name("_calibration_sound")
    assert result == "_calibration_sound_latency"


def test_find_task_not_found_returns_none():
    assert find_task_by_name("nonexistent_xyz_task_abc") is None


def test_find_task_ambiguous_returns_first_alphabetically():
    # "_calibration_liquid" matches both _calibration_liquid_dynamic and _calibration_liquid_static.
    result = find_task_by_name("_calibration_liquid", ignore_error=True)
    matching = sorted(t for t in list_available_tasks() if "_calibration_liquid" in t)
    assert result == matching[0]


# ---------------------------------------------------------------------------
# load_task_module


def test_load_bundled_task_module():
    mod = load_task_module("_calibration_liquid_dynamic")
    assert mod.__file__ is not None
    assert "_calibration_liquid_dynamic" in mod.__file__


def test_load_task_module_via_entry_point():
    ep = _make_ep("ext_task", "murineshiftwork.cli.tasks")
    with patch("murineshiftwork.cli.tasks.entry_points", return_value=[ep]):
        mod = load_task_module("ext_task")
    assert mod is not None


def test_load_task_module_bundled_ignores_absent_entry_point():
    # Even with no entry points registered, bundled tasks load by module path.
    with patch("murineshiftwork.cli.tasks.entry_points", return_value=[]):
        mod = load_task_module("_calibration_liquid_dynamic")
    assert mod.__file__ is not None

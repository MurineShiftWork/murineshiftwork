"""Tests for TaskRunner.get_path(): path helpers on the task runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

_BASE = "/data/mouse_01/mouse_01__20260524_143022_123456__sequence/mouse_01__20260524_143022_123456__sequence"


def test_taskrunner_get_path(tmp_path):
    from murineshiftwork.logic.task_process import TaskRunner

    session_file_path = str(
        tmp_path
        / "mouse_01"
        / "mouse_01__20260524_143022_123456__sequence"
        / "mouse_01__20260524_143022_123456__sequence"
    )

    runner = MagicMock(spec=TaskRunner)
    runner.input_kwargs = {"session_paths": {"session_file_path": session_file_path}}
    runner.get_path = TaskRunner.get_path.__get__(runner, TaskRunner)

    p = runner.get_path("df.jsonl")
    assert str(p) == session_file_path + ".msw.df.jsonl"
    assert isinstance(p, Path)


def test_taskrunner_get_path_session_yaml(tmp_path):
    from murineshiftwork.logic.task_process import TaskRunner

    session_file_path = str(
        tmp_path
        / "mouse_01"
        / "mouse_01__20260524_143022_123456__sequence"
        / "mouse_01__20260524_143022_123456__sequence"
    )

    runner = MagicMock(spec=TaskRunner)
    runner.input_kwargs = {"session_paths": {"session_file_path": session_file_path}}
    runner.get_path = TaskRunner.get_path.__get__(runner, TaskRunner)

    p = runner.get_path("session.yaml")
    assert p.name == "mouse_01__20260524_143022_123456__sequence.msw.session.yaml"

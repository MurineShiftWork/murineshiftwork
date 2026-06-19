"""CLI entry-point registration and dispatch smoke tests."""

from importlib.metadata import entry_points

import pytest
from murineshiftwork.cli.parser import parse_args
from murineshiftwork.cli.tasks import run_tasks_list


def test_console_scripts_registered():
    names = {ep.name for ep in entry_points(group="console_scripts")}
    assert "murineshiftwork" in names
    assert "msw" in names


def test_version_exits_cleanly():
    with pytest.raises(SystemExit) as exc:
        parse_args(["--version"])
    assert exc.value.code == 0


def test_tasks_list_runs(capsys):
    run_tasks_list()
    out = capsys.readouterr().out
    assert isinstance(out, str)
    assert len(out) > 0, (
        "run_tasks_list() produced no output; expected at least one task listed"
    )

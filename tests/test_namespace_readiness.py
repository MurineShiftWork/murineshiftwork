"""Namespace package readiness checks.

These tests verify the structural prerequisites for the future msw-namespace
suite split (msw-logic, msw-tasks-*, msw-agent as separate installable packages).

Namespace split requires that Python treats `murineshiftwork/` as an implicit
namespace package (PEP 420), which means NO __init__.py at the namespace root
or at the tasks/ boundary.  Sub-packages (cli/, logic/, hardware/, etc.) keep
their own __init__.py files — those are normal sub-packages within the namespace.

Both tests now pass: the root __init__.py was removed as part of the CLI refactor.
"""
from pathlib import Path

import murineshiftwork
import pytest

# Namespace packages have __path__ but no __file__ — use __path__[0]
_PKG_ROOT = Path(list(murineshiftwork.__path__)[0])  # .../src/murineshiftwork/
_TASKS_DIR = _PKG_ROOT / "tasks"


def test_tasks_boundary_has_no_init():
    """tasks/ must not have __init__.py so each task sub-package can be
    installed independently as a namespace contributor."""
    init = _TASKS_DIR / "__init__.py"
    assert not init.exists(), (
        f"{init} exists. Remove it to allow task sub-packages "
        f"(msw-tasks-sequence, msw-tasks-ps, …) to contribute to the "
        f"murineshiftwork.tasks namespace independently."
    )


def test_namespace_root_has_no_init():
    """murineshiftwork/ must not have __init__.py — namespace-split ready."""
    init = _PKG_ROOT / "__init__.py"
    assert (
        not init.exists()
    ), f"{init} exists. It must be removed before the suite namespace split."

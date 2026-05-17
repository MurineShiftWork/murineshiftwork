"""Namespace package readiness checks.

These tests verify the structural prerequisites for the future msw-namespace
suite split (msw-logic, msw-tasks-*, msw-agent as separate installable packages).

Namespace split requires that Python treats `murineshiftwork/` as an implicit
namespace package (PEP 420), which means NO __init__.py at the namespace root
or at the tasks/ boundary.  Sub-packages (cli/, logic/, hardware/, etc.) keep
their own __init__.py files — those are normal sub-packages within the namespace.

test_tasks_boundary_has_no_init: PASSES now — tasks/ already has no __init__.py.
test_namespace_root_has_no_init: XFAIL now — murineshiftwork/__init__.py still
  exists (required for the current monolith).  Will start passing once Sprint B
  (namespace split) removes it.
"""
import pytest
from pathlib import Path
import murineshiftwork


_PKG_ROOT = Path(murineshiftwork.__file__).parent   # .../src/murineshiftwork/
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "murineshiftwork/__init__.py still exists (monolith mode). "
        "Sprint B (namespace split) will remove it so Python treats "
        "murineshiftwork/ as an implicit namespace package (PEP 420), "
        "allowing msw-logic, msw-tasks-*, and msw-agent to be installed "
        "as separate packages that all contribute to the same namespace."
    ),
)
def test_namespace_root_has_no_init():
    """murineshiftwork/ must not have __init__.py for the namespace split."""
    init = _PKG_ROOT / "__init__.py"
    assert not init.exists(), (
        f"{init} exists. It must be removed before the suite namespace split."
    )

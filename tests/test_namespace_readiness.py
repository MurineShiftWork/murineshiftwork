"""Namespace package readiness checks.

These tests verify the structural prerequisites for the murineshiftwork
namespace split (murineshiftwork main + msw-io + future msw-tasks-*, msw-agent
as separate installable namespace contributors).

Namespace split requires that Python treats `murineshiftwork/` as an implicit
namespace package (PEP 420), which means NO __init__.py at the namespace root
or at the tasks/ boundary.  Sub-packages (cli/, logic/, hardware/, etc.) keep
their own __init__.py files: those are normal sub-packages within the namespace.

msw-io contributes murineshiftwork.io, murineshiftwork.namespace, and
murineshiftwork.readers. Both contributors must be free of a root __init__.py.
"""

from pathlib import Path

import murineshiftwork

# Namespace packages have __path__ but no __file__: __path__ lists all
# contributor roots (one per installed namespace-contributing package).
_PKG_ROOTS = [Path(p) for p in murineshiftwork.__path__]
_TASKS_DIR = _PKG_ROOTS[0] / "tasks"


def test_tasks_boundary_has_no_init():
    """tasks/ must not have __init__.py so each task sub-package can be
    installed independently as a namespace contributor."""
    init = _TASKS_DIR / "__init__.py"
    assert not init.exists(), (
        f"{init} exists. Remove it to allow task sub-packages "
        f"(msw-tasks-sequence, msw-tasks-ps, ...) to contribute to the "
        f"murineshiftwork.tasks namespace independently."
    )


def test_namespace_root_has_no_init():
    """No contributor must have __init__.py at the murineshiftwork/ root."""
    for root in _PKG_ROOTS:
        init = root / "__init__.py"
        assert not init.exists(), (
            f"{init} exists. All namespace contributors must omit the root "
            f"__init__.py or Python will not treat murineshiftwork/ as an "
            f"implicit namespace package."
        )


def test_msw_io_namespace_subpackages_importable():
    """murineshiftwork.io, .namespace, .readers must resolve from msw-io."""
    from murineshiftwork.io import load_trial_data, save_trial_data  # noqa: F401
    from murineshiftwork.namespace import get_msw_builder  # noqa: F401
    from murineshiftwork.namespace.manifest import (
        init_acquisition_manifest,  # noqa: F401
    )
    from murineshiftwork.readers import MswSession  # noqa: F401

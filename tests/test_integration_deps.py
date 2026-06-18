"""Integration tests for cross-package dependency chains.

These tests verify the full installed stack without mocking:
  - real importlib entry-point discovery (not patched)
  - factory functions resolving to concrete classes from external packages
  - namespace contributors all free of root __init__.py

Requirement: every future namespace package extraction must add tests here that
cover points 2 and 3 for that package (entry-point discovery + factory smoke).
See sop/build_system.md "Namespace package extraction" for the full checklist.

The tests in this file are intentionally not mocked so that entry-point
registration errors (wrong module path, missing class, import failure) are
caught before merge. They run in the CI 'test' and 'integration' jobs which
install with '--extra oe' (full deps chain).
"""

from __future__ import annotations

from importlib.metadata import entry_points

import pytest

msw_open_ephys = pytest.importorskip(
    "msw_open_ephys",
    reason="msw-open-ephys not installed; run: uv sync --extra oe",
)


# ---------------------------------------------------------------------------
# msw.host entry-point group (OE plugin)


def test_msw_host_oe_entry_point_registered():
    """entry_points(group='msw.host') must contain 'openephys' after install."""
    names = {ep.name for ep in entry_points(group="msw.host")}
    assert "openephys" in names, (
        f"'openephys' not found in msw.host entry-points. Got: {names!r}. "
        "Check [project.entry-points.'msw.host'] in msw-open-ephys pyproject.toml."
    )


def test_msw_host_oe_entry_point_loads_correct_class():
    """The 'openephys' entry-point must load OpenEphysHostSession."""
    from msw_open_ephys.host import OpenEphysHostSession

    for ep in entry_points(group="msw.host"):
        if ep.name == "openephys":
            cls = ep.load()
            assert cls is OpenEphysHostSession
            return
    pytest.fail("'openephys' entry-point not found")


# ---------------------------------------------------------------------------
# msw.cli entry-point group (OE subcommand)


def test_msw_cli_oe_entry_point_registered():
    """entry_points(group='msw.cli') must contain 'oe' after install."""
    names = {ep.name for ep in entry_points(group="msw.cli")}
    assert "oe" in names, (
        f"'oe' not found in msw.cli entry-points. Got: {names!r}. "
        "Check [project.entry-points.'msw.cli'] in msw-open-ephys pyproject.toml."
    )


def test_msw_cli_oe_entry_point_loads_register_callable():
    """The 'oe' msw.cli entry-point must load a callable 'register' function."""
    for ep in entry_points(group="msw.cli"):
        if ep.name == "oe":
            register = ep.load()
            assert callable(register)
            return
    pytest.fail("'oe' msw.cli entry-point not found")


# ---------------------------------------------------------------------------
# make_host_session factory (real entry-points, no mock)


def test_make_host_session_resolves_openephys_without_mock():
    """make_host_session('openephys') must instantiate without mocking."""
    from msw_open_ephys.host import OpenEphysHostSession
    from msw_plugin_api import HostSessionProtocol
    from murineshiftwork.hardware.host_session import make_host_session

    client = make_host_session("openephys", url="localhost")
    assert isinstance(client, OpenEphysHostSession)
    assert isinstance(client, HostSessionProtocol)
    assert client.name == "openephys"


# ---------------------------------------------------------------------------
# Namespace contributor integrity (multi-package install)


def test_all_namespace_contributors_have_no_root_init():
    """All murineshiftwork namespace contributors must omit root __init__.py.

    With msw-io installed, murineshiftwork.__path__ contains entries from both
    murineshiftwork main and msw-io. Neither may have a root __init__.py or
    Python will not treat the directory as an implicit namespace package.
    """
    from pathlib import Path

    import murineshiftwork

    roots = list(murineshiftwork.__path__)
    assert len(roots) >= 2, (
        f"Expected >= 2 namespace contributors (murineshiftwork + msw-io), "
        f"got {len(roots)}: {roots}. Is msw-io installed?"
    )
    for root in roots:
        init = Path(root) / "__init__.py"
        assert not init.exists(), (
            f"{init} exists. Namespace contributor at {root!r} must not have "
            "a root __init__.py: it breaks the implicit namespace package."
        )


def test_msw_io_subpackages_importable_with_oe_stack():
    """msw-io namespace contributions remain importable when OE is also installed."""
    from murineshiftwork.io import load_trial_data, save_trial_data  # noqa: F401
    from murineshiftwork.namespace import get_msw_builder  # noqa: F401
    from murineshiftwork.namespace.manifest import (
        init_acquisition_manifest,  # noqa: F401
    )
    from murineshiftwork.readers import MswSession  # noqa: F401

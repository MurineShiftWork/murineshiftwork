"""Host-session plugin system for nesting behavioural sessions inside an
overarching acquisition process.

Activated via ``--host TYPE[:URL]`` and ``--link-to BASENAME`` CLI flags.
No permanent setup-YAML config — sessions opt-in per run.

A host session supplies an acquisition name that MSW passes as ``linked_to``
when building session paths, following the v2 namespace::

    subject/acquisition_name/session_name/

Plugins register under the ``msw.host`` entry-point group::

    [project.entry-points."msw.host"]
    openephys = "msw_open_ephys.host:OpenEphysHostSession"

Usage::

    client = make_host_session("openephys", url="10.0.10.111")
    info = client.attach()
    if info:
        generate_session_paths(..., linked_to=info.acquisition_name)

Plugin contract: docs/concepts/plugin_system.md
"""

from __future__ import annotations

import re
from importlib.metadata import entry_points
from typing import Any

from msw_plugin_api import HostSessionInfo, HostSessionProtocol  # noqa: F401

_SEP = re.compile(r"[-_]")


def _key(s: str) -> str:
    return _SEP.sub("", s.lower())


def make_host_session(session_type: str, **kwargs: Any) -> HostSessionProtocol:
    """Return a HostSessionProtocol implementation for *session_type*.

    Discovers plugins registered under the ``msw.host`` entry-point group.
    Accepts any separator variant of the name (openephys, open-ephys, open_ephys).
    Raises ValueError if no plugin is registered for *session_type*.
    """
    target = _key(session_type)

    for ep in entry_points(group="msw.host"):
        if _key(ep.name) == target:
            cls = ep.load()
            session = cls(**kwargs)
            if not isinstance(session, HostSessionProtocol):
                raise TypeError(
                    f"Plugin {ep.name!r} ({cls}) does not satisfy HostSessionProtocol"
                )
            return session

    raise ValueError(
        f"No msw.host plugin registered for {session_type!r}. "
        f"Install the relevant package (e.g. pip install msw-open-ephys) "
        f"and ensure its entry-point is declared."
    )

"""Parent-session attachment — pluggable system for nesting behavioural sessions
inside an overarching acquisition process.

Activated via CLI flags only (``--parent TYPE[:URL]``, ``--child-of BASENAME``).
No permanent setup-YAML config — sessions opt-in per run without touching shared files.

A parent session supplies an acquisition name that MSW passes as
``is_child_session_to`` when building session paths, following the v2 namespace:

    subject/acquisition_name/session_name/

Usage::

    client = make_parent_session("open_ephys", url="172.24.42.168")
    info = client.attach()
    if info:
        generate_session_paths(..., is_child_session_to=info.acquisition_name)

Adding a new backend:
    1. Implement ParentSessionProtocol.
    2. Register it in make_parent_session() below.
    3. Add a CLI flag in cli/parser.py and a branch in _resolve_parent_session().

Backends
--------
open_ephys : OpenEphysParentSession — reads acquisition path from OE GUI REST API.
             Requires msw-open-ephys (OEController).  Lazy import.
             Previously used open-ephys-python-tools (OpenEphysHTTPServer), replaced
             because that package has unstable API and does not reliably return
             base_text in get_recording_info() across versions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)

_HOST_RE = re.compile(r"(?:https?://)?([^:/]+)")


def _parse_host(url: str) -> str:
    """Extract hostname from a full URL or bare host string."""
    m = _HOST_RE.match(url.strip())
    return m.group(1) if m else url


# ---------------------------------------------------------------------------
# Data types


@dataclass
class ParentSessionInfo:
    """Acquisition context returned by a successful parent session attachment."""

    acquisition_name: str
    subject: str = ""
    parent_directory: str = ""
    backend: str = ""
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocol


@runtime_checkable
class ParentSessionProtocol(Protocol):
    """Structural interface for a parent-session attachment client."""

    name: str

    def attach(self) -> ParentSessionInfo | None:
        """Query the remote system and return session context, or None.

        Returns None when the system is unreachable, not in a recordable state,
        or has not been configured with a valid acquisition path yet.
        """
        ...


# ---------------------------------------------------------------------------
# Open Ephys backend


class OpenEphysParentSession:
    """Attach to a running Open Ephys GUI process via its HTTP REST API.

    Reads the ``base_text`` field set by ``oe_remote`` to extract the
    acquisition folder name.  Expects ``base_text`` to be a 3-part path::

        subject / acquisition_name / oe_session_name

    as written by ``oe_remote session.py``.  If ``base_text`` has fewer than
    two parts (OE default template not yet replaced by oe_remote), returns None
    and logs a warning.

    All open_ephys.control imports are deferred so the package is not required
    on machines that do not use Open Ephys.
    """

    name = "open_ephys"

    def __init__(self, url: str, require_recording: bool = False) -> None:
        self._host = _parse_host(url)
        self._require_recording = require_recording
        self.fail_reason: str = ""

    def attach(self) -> ParentSessionInfo | None:
        try:
            from msw_open_ephys.controller import OEController
        except ImportError:
            self.fail_reason = (
                "msw-open-ephys not installed (pip install msw-open-ephys)"
            )
            log.error("OpenEphys: %s", self.fail_reason)
            return None

        gui = OEController(ip=self._host)

        try:
            status = gui.status
        except Exception as exc:
            self.fail_reason = f"cannot reach {self._host} — {exc}"
            log.error("OpenEphys: %s", self.fail_reason)
            return None

        if self._require_recording and status != "RECORD":
            self.fail_reason = f"status={status!r} (not RECORD)"
            log.info("OpenEphys: %s — no parent session attached", self.fail_reason)
            return None

        try:
            rec = gui.recording
        except Exception as exc:
            self.fail_reason = f"GET /api/recording failed — {exc}"
            log.error("OpenEphys: %s", self.fail_reason)
            return None

        log.debug("OpenEphys /api/recording: %s", rec)

        base = (rec.get("base_text") or "").strip("/")
        parts = [p for p in base.split("/") if p]
        log.debug("OpenEphys base_text=%r → parts=%s", base, parts)

        if len(parts) < 2:
            self.fail_reason = (
                f"base_text {base!r} has <2 parts — "
                f"run oe_remote session before msw run, or use --child-of ACQUISITION_NAME"
            )
            log.error("OpenEphys: %s", self.fail_reason)
            return None

        # Validate the acquisition segment through the namespace builder so the
        # format is checked against the MSW session spec.
        acq_segment = parts[1]
        try:
            from murineshiftwork.namespace.paths import get_msw_builder

            _b = get_msw_builder()
            acquisition_name = _b.build_path(
                "session", _b.extract_level_values("session", acq_segment)
            )
        except ValueError:
            self.fail_reason = (
                f"base_text segment {acq_segment!r} is not a valid MSW session name "
                f"(full base_text: {base!r}) — check oe_remote naming convention"
            )
            log.error("OpenEphys: %s", self.fail_reason)
            return None

        record_nodes = rec.get("record_nodes") or []
        parent_dir = record_nodes[0].get("parent_directory", "") if record_nodes else ""

        return ParentSessionInfo(
            acquisition_name=acquisition_name,
            subject=parts[0],
            parent_directory=parent_dir,
            backend="open_ephys",
            extra={
                "oe_session_name": parts[2] if len(parts) > 2 else "",
                "status": status,
            },
        )


# ---------------------------------------------------------------------------
# Factory


def make_parent_session(session_type: str, **kwargs: Any) -> ParentSessionProtocol:
    """Return a ParentSessionProtocol implementation for *session_type*.

    Example::

        client = make_parent_session("open_ephys", url="172.24.42.168")
    """
    normalised = session_type.replace("-", "_").lower()
    if normalised in ("open_ephys", "openephys"):
        return OpenEphysParentSession(**kwargs)
    raise ValueError(f"Unknown parent session type: {session_type!r}")

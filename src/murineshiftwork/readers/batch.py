"""Batch loading API for MSW sessions.

Public surface:
  load_session(session_dir)           -> MswSession
  load_acquisition(acquisition_dir)   -> list[MswSession]
  load_subject(subject_dir)           -> list[MswSession]
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from murineshiftwork.readers.models import MswSession
from murineshiftwork.readers.session import read_session_data

log = logging.getLogger(__name__)


def _parse_identity(session_dir: Path) -> dict:
    """Return subject/datetime_str/task from the session dir basename.

    Falls back to empty strings when the basename doesn't match the namespace
    pattern (e.g. unnamed test dirs) so callers always get a MswSession.
    """
    from murineshiftwork.namespace.paths import parse_session_basename
    from murineshiftwork.readers.namespace import _infer_session_basename

    basename = _infer_session_basename(session_dir) or session_dir.name
    try:
        info = parse_session_basename(basename)
        return {
            "basename": basename,
            "subject": info["subject"],
            "datetime_str": info["datetime_str"],
            "task": info["task"],
        }
    except Exception:
        return {"basename": basename, "subject": "", "datetime_str": "", "task": ""}


def load_session(
    session_dir,
    *,
    acquisition_name: str | None = None,
    acquisition_dir: Path | None = None,
) -> MswSession:
    """Read one session directory and return a structured MswSession.

    Parameters
    ----------
    session_dir:
        Path to the MSW session directory.
    acquisition_name:
        Optional — set when called from load_acquisition().
    acquisition_dir:
        Optional — set when called from load_acquisition().
    """
    session_dir = Path(session_dir)
    raw = read_session_data(session_dir)
    identity = _parse_identity(session_dir)

    return MswSession(
        session_dir=session_dir,
        basename=identity["basename"],
        subject=identity["subject"],
        datetime_str=identity["datetime_str"],
        task=identity["task"],
        namespace_version=raw.get("namespace_version"),
        artifact_format=raw["artifact_format"],
        msw_version=raw.get("msw_version", ""),
        df=raw.get("df"),
        settings_task=raw.get("settings.task"),
        settings_process=raw.get("settings.process"),
        settings_stage=raw.get("settings.stage"),
        settings_ephys=raw.get("settings.ephys"),
        subprotocols=raw.get("subprotocols"),
        is_complete=raw.get("is_complete_session", False),
        is_ephys=raw.get("is_ephys_session", False),
        acquisition_name=acquisition_name,
        acquisition_dir=acquisition_dir,
    )


def load_acquisition(acquisition_dir) -> list[MswSession]:
    """Load all acquisitions inside a session container directory.

    ``acquisition_dir`` is the SESSION container (e.g. an Open Ephys recording
    dir, or a standalone MSW session wrapper) that holds one or more MSW
    acquisition subdirectories.

    Reads acquisition_manifest.yaml when present to determine which acquisition
    dirs to load.  Falls back to scanning for subdirectories whose name
    contains ``__`` (MSW basename-like).

    Returns sessions sorted by datetime_str (ascending).
    """
    acquisition_dir = Path(acquisition_dir)
    acquisition_name = acquisition_dir.name

    manifest_path = acquisition_dir / "acquisition_manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        session_dirs = []
        for s in manifest.get("sessions", []):
            # schema uses "basename"; older writes may have used "session_dir"
            name = s.get("basename") or s.get("session_dir")
            if name:
                d = acquisition_dir / name
                if d.is_dir():
                    session_dirs.append(d)
    else:
        # heuristic: subdirs whose name contains "__" (basename-like)
        session_dirs = sorted(
            d for d in acquisition_dir.iterdir() if d.is_dir() and "__" in d.name
        )

    sessions = []
    for sd in session_dirs:
        try:
            sess = load_session(
                sd,
                acquisition_name=acquisition_name,
                acquisition_dir=acquisition_dir,
            )
            sessions.append(sess)
        except Exception as exc:
            log.warning("load_acquisition: skipping %s — %s", sd, exc)

    sessions.sort(key=lambda s: s.datetime_str)
    return sessions


def _has_session_files(directory: Path) -> bool:
    """True if *directory* directly contains any MSW or legacy session files."""
    from murineshiftwork.readers.namespace import test_is_recognized_msw_file

    try:
        return any(
            test_is_recognized_msw_file(f) for f in directory.iterdir() if f.is_file()
        )
    except PermissionError:
        return False


def load_subject(subject_dir) -> list[MswSession]:
    """Load all sessions under a subject directory.

    Current layout (all new sessions, both standalone and host-linked)::

        subject_dir / session_container / acquisition_dir /   (3-level)

    Legacy layout (pre-rename standalone sessions, no session container)::

        subject_dir / session_dir /   (2-level, backward compat)

    Detection is file-based: a child directory that directly contains .msw.
    files is a legacy session dir (load directly); a child directory that
    contains no .msw. files but has ``__``-named subdirs is a session container
    (call load_acquisition to walk its acquisition dirs).

    Returns sessions sorted by datetime_str (ascending).
    """
    subject_dir = Path(subject_dir)
    sessions: list[MswSession] = []

    for child in sorted(subject_dir.iterdir()):
        if not child.is_dir():
            continue
        if _has_session_files(child):
            # legacy 2-level: session dir directly under subject (backward compat)
            try:
                sessions.append(load_session(child))
            except Exception as exc:
                log.warning("load_subject: skipping %s — %s", child, exc)
        else:
            # current 3-level: subject / session_container / acquisition_dir
            nested_sessions = [
                d for d in child.iterdir() if d.is_dir() and "__" in d.name
            ]
            if nested_sessions:
                sessions.extend(load_acquisition(child))

    sessions.sort(key=lambda s: s.datetime_str)
    return sessions

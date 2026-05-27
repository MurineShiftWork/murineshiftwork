"""Acquisition and session manifest writers.

Manifests are YAML files written progressively during a session:
  acquisition_manifest.yaml  — inside the acquisition dir; lists sessions
  session_manifest.yaml      — inside the session dir; lists subprotocols (opto) or empty

All write operations are atomic (write temp file, rename).
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _write_yaml(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".yaml.tmp")
    with tmp.open("w") as f:
        yaml.dump(
            data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Acquisition manifest


def init_acquisition_manifest(
    acquisition_folder: str | Path, acquisition_name: str
) -> None:
    """Create acquisition_manifest.yaml if it does not exist."""
    p = Path(acquisition_folder) / "acquisition_manifest.yaml"
    if p.exists():
        return
    _write_yaml(
        p,
        {
            "msw_manifest_version": 1,
            "type": "acquisition",
            "acquisition_name": acquisition_name,
            "sessions": [],
        },
    )


def append_session_to_acquisition(
    acquisition_folder: str | Path,
    session_basename: str,
    started_at: str | None = None,
) -> None:
    """Add a session entry (status=running). Call at TaskProcess init."""
    p = Path(acquisition_folder) / "acquisition_manifest.yaml"
    data: dict[str, Any] = (
        _read_yaml(p)
        if p.exists()
        else {"msw_manifest_version": 1, "type": "acquisition", "sessions": []}
    )
    sessions = data.setdefault("sessions", [])
    if not any(s.get("basename") == session_basename for s in sessions):
        sessions.append(
            {
                "basename": session_basename,
                "started_at": started_at or _now_iso(),
                "ended_at": None,
                "status": "running",
            }
        )
    _write_yaml(p, data)


def finalize_session_in_acquisition(
    acquisition_folder: str | Path,
    session_basename: str,
    status: str = "complete",
    ended_at: str | None = None,
) -> None:
    """Set status and ended_at. Call at TaskProcess exit."""
    p = Path(acquisition_folder) / "acquisition_manifest.yaml"
    if not p.exists():
        return
    data = _read_yaml(p)
    for s in data.get("sessions", []):
        if s.get("basename") == session_basename:
            s["status"] = status
            s["ended_at"] = ended_at or _now_iso()
            break
    _write_yaml(p, data)


# ---------------------------------------------------------------------------
# Session manifest


def init_session_manifest(session_folder: str | Path, session_basename: str) -> None:
    """Write session_manifest.yaml with empty subprotocols. Call at session start."""
    p = Path(session_folder) / "session_manifest.yaml"
    if p.exists():
        return
    _write_yaml(
        p,
        {
            "msw_manifest_version": 1,
            "type": "session",
            "session_basename": session_basename,
            "subprotocols": [],
        },
    )


def append_subprotocol(
    session_folder: str | Path,
    name: str,
    filename: str,
    barcode_start: int | None = None,
) -> None:
    """Add a subprotocol entry (status=running). Call before each opto protocol."""
    p = Path(session_folder) / "session_manifest.yaml"
    data: dict[str, Any] = (
        _read_yaml(p)
        if p.exists()
        else {"msw_manifest_version": 1, "type": "session", "subprotocols": []}
    )
    protos = data.setdefault("subprotocols", [])
    if not any(sp.get("name") == name for sp in protos):
        protos.append(
            {
                "name": name,
                "file": filename,
                "barcode_start": barcode_start,
                "barcode_end": None,
                "status": "running",
            }
        )
    _write_yaml(p, data)


def finalize_subprotocol(
    session_folder: str | Path,
    name: str,
    barcode_end: int | None = None,
    status: str = "complete",
) -> None:
    """Set barcode_end and status. Call in finally block after each opto protocol."""
    p = Path(session_folder) / "session_manifest.yaml"
    if not p.exists():
        return
    data = _read_yaml(p)
    for sp in data.get("subprotocols", []):
        if sp.get("name") == name:
            sp["barcode_end"] = barcode_end
            sp["status"] = status
            break
    _write_yaml(p, data)

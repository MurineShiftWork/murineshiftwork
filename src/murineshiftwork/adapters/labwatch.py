"""Labwatch session push adapter.

Thin interface over the labwatch client (private registry, optional dependency).
The only method MSW calls is `LabwatchPusher.push(payload)`.

Usage in save_session_end():
    pusher = LabwatchPusher.from_machine_config(read_machine_config())
    if pusher:
        push_session_threaded(pusher, build_labwatch_payload(...), retry_path)
"""

from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class LabwatchPushError(Exception):
    pass


class LabwatchPusher:
    """Adapter over the labwatch client.

    `push()` is the single method MSW calls. The labwatch client import is
    deferred so a missing or unconfigured dependency never crashes a session.
    """

    def __init__(self, url: str, username: str = "", password: str = "") -> None:
        self.url = url
        self.username = username
        self.password = password

    @classmethod
    def from_machine_config(cls, cfg: dict) -> LabwatchPusher | None:
        """Return a pusher if labwatch is configured, else None."""
        lw = cfg.get("labwatch", {})
        if not lw or not lw.get("url"):
            return None
        return cls(
            url=lw["url"],
            username=lw.get("username", ""),
            password=lw.get("password", lw.get("token", "")),
        )

    def push(self, payload: dict[str, Any]) -> None:
        """Upsert session record in labwatch.

        Raises LabwatchPushError on any failure so the caller can handle
        retry-file writing without catching broad exceptions.
        """
        try:
            from labwatch_client import Client  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LabwatchPushError(
                "labwatch_client is not installed. "
                "Install with: pip install 'murineshiftwork[labwatch]'"
            ) from exc

        try:
            client = Client(
                url=self.url,
                username=self.username,
                password=self.password,
            )
            client.sessions.upsert(payload)
        except Exception as exc:
            raise LabwatchPushError(str(exc)) from exc


def build_labwatch_payload(
    session_yaml: dict[str, Any],
    task_summary: dict[str, Any],
) -> dict[str, Any]:
    """Map MSW session data to the labwatch session schema.

    The `session_basename` field is the idempotency key — pushing the same
    session twice produces an upsert, not a duplicate.
    """
    proc = session_yaml.get("process", {})
    return {
        "session_id": proc.get("session_basename", ""),
        "subject": proc.get("subject", ""),
        "task": proc.get("task", ""),
        "setup": proc.get("setup", ""),
        "datetime": proc.get("datetime", ""),
        "msw_version": proc.get("msw_version", ""),
        "git_commit": proc.get("git_commit", ""),
        "session_folder": proc.get("session_folder", ""),
        "n_trials": task_summary.get("total_trials", 0),
        "task_data": task_summary,
    }


def push_session_threaded(
    pusher: LabwatchPusher,
    payload: dict[str, Any],
    retry_path: Path,
) -> None:
    """Fire-and-forget push in a daemon thread.

    On failure: logs a warning and writes payload to `retry_path` on disk.
    Network issues never block session exit.
    """

    def _do() -> None:
        try:
            pusher.push(payload)
            log.info(
                f"Labwatch: session '{payload.get('session_id', '?')}' pushed successfully."
            )
        except LabwatchPushError as exc:
            log.warning(f"Labwatch push failed (saved to {retry_path}): {exc}")
            try:
                retry_path.parent.mkdir(parents=True, exist_ok=True)
                retry_path.write_text(json.dumps(payload, indent=2))
            except Exception as write_exc:
                log.warning(f"Could not write labwatch retry file: {write_exc}")

    threading.Thread(target=_do, daemon=True, name="labwatch-push").start()

"""LogAgent — daemon process that forwards session events to the central UI server.

Lifecycle (one process per session, daemon=True so it dies with the parent):
  1. run() opens by POSTing session_start_payload to /ingest/{setup}/start
  2. Loops reading from queue; each item is an opaque trial_data dict the task
     put via put_nowait().  Posts each as /ingest/{setup}/trial.
  3. Exits when it reads None (from TaskProcess.exit_safely) or a dict with
     __stop__=True (optional rich sentinel from the task with a summary).
     Sends /ingest/{setup}/stop before exiting.

Fire-and-forget guarantee: put_nowait() in the task loop is ~1 µs regardless
of network state.  All HTTP errors are logged at DEBUG and dropped silently.
Queue(maxsize=500) absorbs bursts; overflow drops silently in the task loop.

Configured via msw_machine.yaml:
  log_url: http://monitor-host:8080
  log_bearer_token: <your-token-here>   # optional; omit to disable auth
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import urllib.request
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class LogAgent(multiprocessing.Process):
    def __init__(
        self,
        queue: multiprocessing.Queue,
        log_url: str,
        setup: str,
        session_start_payload: dict,
        session_uuid: str = "",
        bearer_token: str = "",
    ) -> None:
        super().__init__(daemon=True)
        self._queue = queue
        self._log_url = log_url.rstrip("/")
        self._setup = setup
        self._session_uuid = session_uuid
        self._bearer_token = bearer_token
        self._session_start_payload = session_start_payload

    def run(self) -> None:
        self._post("start", self._session_start_payload)
        while True:
            try:
                event = self._queue.get(block=True, timeout=5)
            except Exception:
                continue
            if event is None:
                self._post("stop", {"ended_at": _now_iso()})
                break
            if isinstance(event, dict) and event.get("__stop__"):
                summary = dict(event.get("summary", {}))
                summary["ended_at"] = _now_iso()
                self._post("stop", summary)
                break
            self._post("trial", {"trial_data": event})

    def _post(self, endpoint: str, payload: dict) -> None:
        url = f"{self._log_url}/ingest/{self._setup}/{endpoint}"
        if self._session_uuid:
            payload = {**payload, "session_uuid": self._session_uuid}
        data = json.dumps(payload, default=str).encode()
        headers = {"Content-Type": "application/json"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            urllib.request.urlopen(req, timeout=0.5)
        except Exception as exc:
            logging.debug("LogAgent POST failed (%s): %s", endpoint, exc)

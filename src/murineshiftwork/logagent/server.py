"""MSW ingest server — receives trial events from LogAgent and exposes
session status for polling clients (Vue UI, CLI status command).

Ingest endpoints (called by LogAgent, protected by bearer token when configured):
  POST /ingest/{setup}/start   — session started
  POST /ingest/{setup}/trial   — one trial
  POST /ingest/{setup}/stop    — session ended

Read endpoints (polled by UI — no auth required):
  GET  /session/status/{setup} — current state + counters
  GET  /session/status         — all setups
  GET  /health                 — {"status": "ok"}

Auth: set log_bearer_token in ~/.murineshiftwork/msw_machine.yaml.
      LogAgent reads the same key and injects Authorization: Bearer <token>.
      Omit the key on both sides to run without auth.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException

_sessions: dict[str, _SessionState] = {}


class _SessionState:
    def __init__(self, setup: str) -> None:
        self.setup = setup
        self.state = "idle"
        self.subject: str | None = None
        self.task: str | None = None
        self.session_uuid: str | None = None
        self.started_at: str | None = None
        self.trial_buffer: deque[dict[str, Any]] = deque(maxlen=1000)

    @property
    def trial_count(self) -> int:
        return len(self.trial_buffer)

    @property
    def reward_count(self) -> int:
        return sum(t.get("reward_count_trial", 0) for t in self.trial_buffer)

    @property
    def liquid_ul(self) -> float:
        return sum(t.get("liquid_ul_trial", 0.0) for t in self.trial_buffer)

    def elapsed_s(self) -> float | None:
        if not self.started_at:
            return None
        try:
            t0 = datetime.fromisoformat(self.started_at)
            return (datetime.now(UTC) - t0).total_seconds()
        except Exception:
            return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "setup": self.setup,
            "session_uuid": self.session_uuid,
            "subject": self.subject,
            "task": self.task,
            "started_at": self.started_at,
            "trial_count": self.trial_count,
            "reward_count": self.reward_count,
            "liquid_ul": round(self.liquid_ul, 1),
            "elapsed_s": self.elapsed_s(),
        }


def _get_or_create(setup: str) -> _SessionState:
    if setup not in _sessions:
        _sessions[setup] = _SessionState(setup)
    return _sessions[setup]


def create_app(bearer_token: str = "") -> FastAPI:
    app = FastAPI(title="MSW LogAgent Server", version="0.1.0")

    def _verify_token(authorization: str = Header(default="")) -> None:
        if bearer_token and authorization != f"Bearer {bearer_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/ingest/{setup}/start",
        status_code=204,
        dependencies=[Depends(_verify_token)],
    )
    def ingest_start(setup: str, body: dict[str, Any]) -> None:
        sess = _get_or_create(setup)
        sess.state = "running"
        sess.subject = body.get("subject")
        sess.task = body.get("task")
        sess.session_uuid = body.get("session_uuid")
        sess.started_at = body.get(
            "started_at",
            datetime.now(UTC).isoformat(timespec="seconds"),
        )
        sess.trial_buffer.clear()

    @app.post(
        "/ingest/{setup}/trial",
        status_code=204,
        dependencies=[Depends(_verify_token)],
    )
    def ingest_trial(setup: str, body: dict[str, Any]) -> None:
        sess = _get_or_create(setup)
        # LogAgent wraps trial dicts as {"trial_data": {...}}; unwrap for storage
        trial = body.get("trial_data", body)
        sess.trial_buffer.append(trial)

    @app.post(
        "/ingest/{setup}/stop",
        status_code=204,
        dependencies=[Depends(_verify_token)],
    )
    def ingest_stop(setup: str, body: dict[str, Any]) -> None:
        sess = _get_or_create(setup)
        sess.state = "idle"

    @app.get("/session/status/{setup}")
    def session_status(setup: str) -> dict[str, Any]:
        if setup not in _sessions:
            raise HTTPException(404, f"No session data for setup {setup!r}")
        return _sessions[setup].as_dict()

    @app.get("/session/status")
    def session_status_all() -> dict[str, Any]:
        return {s: state.as_dict() for s, state in _sessions.items()}

    return app

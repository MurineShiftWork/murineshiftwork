from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from murineshiftwork.agent.models import SessionInfo, SessionStatus

if TYPE_CHECKING:
    import asyncio


class SessionManager:
    """Owns the lifecycle of one TaskProcess at a time.

    - `start()` launches a TaskProcess in a background thread.
    - `stop()` signals it to stop and waits for clean exit.
    - Events from the running task are pushed to all registered WebSocket queues.
    """

    def __init__(self) -> None:
        self._status = SessionStatus.idle
        self._subject: str | None = None
        self._task: str | None = None
        self._setup: str | None = None
        self._started_at: str | None = None
        self._trial_index: int = 0
        self._process: object | None = None
        self._ws_queues: list[asyncio.Queue] = []

    # ------------------------------------------------------------------
    # Public API

    def start(
        self, subject: str, task: str, setup: str, args_dict: dict[str, Any]
    ) -> None:
        if self._status == SessionStatus.running:
            raise RuntimeError("A session is already running. Stop it first.")

        from murineshiftwork.logic.task_process import TaskProcess

        self._subject = subject
        self._task = task
        self._setup = setup
        self._started_at = datetime.now(UTC).isoformat(timespec="seconds")
        self._trial_index = 0
        self._status = SessionStatus.running

        proc = TaskProcess(**args_dict)
        self._process = proc
        proc.run_task()
        logging.info(f"SessionManager: started task={task!r} subject={subject!r}")

    def stop(self) -> None:
        if self._status != SessionStatus.running or self._process is None:
            return
        self._status = SessionStatus.stopping
        if hasattr(self._process, "stop_task"):
            self._process.stop_task()  # type: ignore[attr-defined]
        logging.info("SessionManager: stop requested.")

    def update_trial(self, trial_index: int) -> None:
        self._trial_index = trial_index

    def mark_idle(self) -> None:
        self._status = SessionStatus.idle
        self._process = None

    # ------------------------------------------------------------------
    # WebSocket broadcast

    def register_ws(self, q: asyncio.Queue) -> None:
        self._ws_queues.append(q)

    def unregister_ws(self, q: asyncio.Queue) -> None:
        with contextlib.suppress(ValueError):
            self._ws_queues.remove(q)

    async def broadcast(self, event: dict[str, Any]) -> None:
        for q in list(self._ws_queues):
            await q.put(event)

    # ------------------------------------------------------------------
    # State

    @property
    def status(self) -> SessionStatus:
        return self._status

    def info(self) -> SessionInfo:
        return SessionInfo(
            status=self._status,
            subject=self._subject,
            task=self._task,
            setup=self._setup,
            trial_index=self._trial_index,
            started_at=self._started_at,
        )

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class HardwareStatus(StrEnum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class SessionStatus(StrEnum):
    idle = "idle"
    running = "running"
    stopping = "stopping"


class HardwareStatusResponse(BaseModel):
    bpod: HardwareStatus
    bpod_port: str | None = None
    setup: str | None = None


class SessionStartRequest(BaseModel):
    subject: str
    task: str
    setup: str
    overrides: dict[str, Any] = {}


class SessionInfo(BaseModel):
    status: SessionStatus
    subject: str | None = None
    task: str | None = None
    setup: str | None = None
    trial_index: int = 0
    started_at: str | None = None


class EventMessage(BaseModel):
    type: str
    payload: dict[str, Any] = {}

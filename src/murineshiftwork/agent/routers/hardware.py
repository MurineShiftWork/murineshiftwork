from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from murineshiftwork.agent.models import HardwareStatusResponse

router = APIRouter(prefix="/hardware", tags=["hardware"])


@router.get("/status", response_model=HardwareStatusResponse)
def get_hardware_status(request: Request) -> HardwareStatusResponse:
    hw = request.app.state.hardware
    return hw.status()


@router.post("/reconnect", response_model=HardwareStatusResponse)
def reconnect_hardware(request: Request) -> HardwareStatusResponse:
    hw = request.app.state.hardware
    session = request.app.state.session
    if session.status.value == "running":
        raise HTTPException(
            409, "Cannot reconnect hardware while a session is running."
        )
    try:
        hw.reconnect()
    except Exception as exc:
        raise HTTPException(500, f"Reconnect failed: {exc}") from exc
    return hw.status()

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from murineshiftwork.agent.models import SessionInfo, SessionStartRequest, SessionStatus

router = APIRouter(prefix="/session", tags=["session"])


@router.get("/active", response_model=SessionInfo)
def get_active_session(request: Request) -> SessionInfo:
    return request.app.state.session.info()


@router.post("/start", response_model=SessionInfo, status_code=202)
def start_session(body: SessionStartRequest, request: Request) -> SessionInfo:
    session = request.app.state.session
    hw = request.app.state.hardware

    if session.status == SessionStatus.running:
        raise HTTPException(409, "A session is already running.")
    if not hw.is_connected:
        raise HTTPException(
            503, "Hardware not connected. Call POST /hardware/reconnect first."
        )

    from murineshiftwork.cli.evaluate import evaluate_args

    args_dict: dict = {
        "command": "run",
        "subject": body.subject,
        "task": body.task,
        "setup": body.setup,
        "bpod": hw.bpod,
        "_agent_injected_bpod": True,
    }
    args_dict.update(body.overrides)
    try:
        args_dict = evaluate_args(args_dict=args_dict)
    except Exception as exc:
        raise HTTPException(422, f"Config evaluation failed: {exc}") from exc

    try:
        session.start(
            subject=body.subject,
            task=body.task,
            setup=body.setup,
            args_dict=args_dict,
        )
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

    logging.info(f"Agent: session started for {body.subject!r} / {body.task!r}")
    return session.info()


@router.delete("/active", status_code=202)
def stop_session(request: Request) -> dict:
    session = request.app.state.session
    if session.status != SessionStatus.running:
        raise HTTPException(404, "No running session to stop.")
    session.stop()
    return {"detail": "Stop signal sent."}


@router.websocket("/events")
async def session_events(websocket: WebSocket, request: Request) -> None:
    """WebSocket endpoint — pushes session events to read-only observers."""
    session = request.app.state.session
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue()
    session.register_ws(q)
    try:
        while True:
            event = await q.get()
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        session.unregister_ws(q)

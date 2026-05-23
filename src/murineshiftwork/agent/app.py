from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from murineshiftwork.agent.hardware_manager import HardwareManager
from murineshiftwork.agent.routers import config, hardware, session
from murineshiftwork.agent.session_manager import SessionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_security = HTTPBasic()
_MSW_AGENT_PASSWORD_ENV = "MSW_AGENT_PASSWORD"


def _check_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    expected = os.environ.get(_MSW_AGENT_PASSWORD_ENV, "")
    if not expected:
        return credentials.username
    ok = secrets.compare_digest(credentials.password.encode(), expected.encode())
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def create_app(
    setup: str,
    serial_port: str,
    config_dir: str,
) -> FastAPI:
    hw = HardwareManager(setup=setup, serial_port=serial_port)
    sess = SessionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.hardware = hw
        app.state.session = sess
        app.state.config_dir = config_dir
        try:
            hw.connect()
        except Exception:
            logging.warning(
                "Agent: Bpod connect failed at startup — call /hardware/reconnect"
            )
        yield
        hw.disconnect()
        logging.info("Agent: shutdown complete.")

    app = FastAPI(
        title="MSW Agent",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(_check_auth)]
        if os.environ.get(_MSW_AGENT_PASSWORD_ENV)
        else [],
    )

    app.include_router(hardware.router)
    app.include_router(session.router)
    app.include_router(config.router)

    return app

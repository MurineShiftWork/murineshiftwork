from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from murineshiftwork.hardware.bpod.factory import BpodFactory

log = logging.getLogger(__name__)


class BpodDevice:
    """DeviceProtocol implementation wrapping BpodFactory.

    Satisfies hardware.manager.DeviceProtocol structurally (no inheritance).
    HardwareManager calls preflight → connect → [task] → disconnect.

    preflight: checks serial port path exists on disk.
    connect:   creates BpodFactory and calls open() with retry.
    disconnect: calls close_safely() — idempotent, safe to call twice.
    handle:    returns the BpodFactory instance for injection into TaskProcess.
    """

    name = "bpod"

    def __init__(self, serial_port: str, **factory_kwargs: Any) -> None:
        self._serial_port = serial_port
        self._factory_kwargs = factory_kwargs
        self._factory: BpodFactory | None = None

    def preflight(self) -> None:
        log.debug("Bpod preflight: checking port %s", self._serial_port)
        if not Path(self._serial_port).exists():
            raise ValueError(f"Bpod serial port not accessible: {self._serial_port!r}")
        log.debug("Bpod preflight: port exists")

    def connect(self) -> None:
        self._factory = BpodFactory(
            serial_port=self._serial_port, **self._factory_kwargs
        )
        self._factory.open()

    def disconnect(self) -> None:
        log.debug("Bpod disconnect: closing")
        if self._factory is not None:
            self._factory.close_safely()

    @property
    def handle(self) -> BpodFactory:
        if self._factory is None:
            raise RuntimeError(
                "BpodDevice not connected — call connect() before accessing handle"
            )
        return self._factory

from __future__ import annotations

import logging

from murineshiftwork.agent.models import HardwareStatus, HardwareStatusResponse


class HardwareManager:
    """Owns the Bpod connection across sessions.

    Opened once at agent startup, held until agent shuts down.
    Sessions borrow the open bpod object rather than creating their own.
    """

    def __init__(self, setup: str, serial_port: str) -> None:
        self.setup = setup
        self.serial_port = serial_port
        self._bpod: object | None = None
        self._status = HardwareStatus.disconnected

    def connect(self) -> None:
        from murineshiftwork.hardware.bpod.factory import BpodFactory

        try:
            bpod = BpodFactory(serial_port=self.serial_port)
            bpod.open()
            self._bpod = bpod
            self._status = HardwareStatus.connected
            logging.info(f"HardwareManager: Bpod connected on {self.serial_port}")
        except Exception as exc:
            self._status = HardwareStatus.error
            logging.error(f"HardwareManager: Bpod connect failed: {exc}")
            raise

    def disconnect(self) -> None:
        if self._bpod is not None:
            try:
                self._bpod.close()  # type: ignore[attr-defined]
            except Exception as exc:
                logging.warning(f"HardwareManager: error on disconnect: {exc}")
            finally:
                self._bpod = None
                self._status = HardwareStatus.disconnected
                logging.info("HardwareManager: Bpod disconnected.")

    def reconnect(self) -> None:
        self.disconnect()
        self.connect()

    @property
    def bpod(self):
        return self._bpod

    @property
    def is_connected(self) -> bool:
        return self._status == HardwareStatus.connected

    def status(self) -> HardwareStatusResponse:
        return HardwareStatusResponse(
            bpod=self._status,
            bpod_port=self.serial_port,
            setup=self.setup,
        )

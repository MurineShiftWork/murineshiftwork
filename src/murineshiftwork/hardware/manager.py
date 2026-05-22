"""Hardware lifecycle manager.

DeviceProtocol — structural interface any device must satisfy.
HardwareManager — opens/closes a list of devices; returns handles dict.

Usage (controller or CLI):
    with HardwareManager([BpodDevice(port)]) as devices:
        TaskProcess(..., bpod=devices["bpod"])

Bpod is the first concrete implementation.  Future devices (Harp, PyControl,
Scale, PulsePal) implement the same protocol; tasks receive only the handle
and are unaware of the device type.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)


@runtime_checkable
class DeviceProtocol(Protocol):
    """Structural interface for a managed hardware device.

    Implementations must be usable as a context manager so HardwareManager
    can stack them with contextlib.ExitStack.
    """

    name: str

    def preflight(self) -> None:
        """Verify the device is reachable before opening the connection.

        Raise ValueError or IOError with a human-readable message on failure.
        """
        ...

    def connect(self) -> None:
        """Open the hardware connection.  Raise RuntimeError on failure after retries."""
        ...

    def disconnect(self) -> None:
        """Close the hardware connection gracefully."""
        ...

    @property
    def handle(self) -> Any:
        """Return the raw device handle to pass to the task (e.g. a Bpod instance)."""
        ...


class HardwareManager:
    """Open a list of devices in order; close all on exit.

    Call chain:
        HardwareManager([BpodDevice(port)])
          → __enter__
            → BpodDevice.preflight()   # port accessible?
            → BpodDevice.connect()     # BpodFactory.open() with retry
          → returns {"bpod": <Bpod handle>}
          → [task runs]
          → __exit__
            → BpodDevice.disconnect()  # BpodFactory.close_safely()

    Devices that fail preflight raise immediately; connect failures propagate
    the exception from the device layer (RuntimeError with human-readable msg).
    """

    def __init__(self, devices: list[DeviceProtocol]) -> None:
        self._devices = devices
        self._opened: list[DeviceProtocol] = []

    def open(self) -> dict[str, Any]:
        for device in self._devices:
            log.debug("Hardware preflight: %s", device.name)
            device.preflight()
            log.debug("Hardware connect: %s", device.name)
            device.connect()
            self._opened.append(device)
        return {d.name: d.handle for d in self._opened}

    def close(self) -> None:
        for device in reversed(self._opened):
            try:
                log.debug("Hardware disconnect: %s", device.name)
                device.disconnect()
            except Exception:
                log.warning("Error disconnecting %s", device.name, exc_info=True)
        self._opened.clear()

    def __enter__(self) -> dict[str, Any]:
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

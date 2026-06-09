"""Direct firmware-level Bpod output control via manual_override().

Intended for:
  - Interactive hardware testing outside a running state machine
  - Setup-agent session between trials (Stage 6 of agent architecture)
  - Scripted reward delivery during free-running epochs

All methods acquire bpod._write_lock if it exists, so they are safe
to call concurrently with the state machine (Phase 2 / agent mode).
"""

import contextlib
import time
from typing import Any

from pybpodapi.bpod.hardware.channels import ChannelName, ChannelType


class BpodOverrideAPI:
    """High-level wrapper around Bpod manual_override for output control.

    Parameters
    ----------
    bpod:
        An open BpodFactory (or SimBpod) instance.
    """

    def __init__(self, bpod: Any) -> None:
        self._bpod = bpod

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def _lock(self):
        lock = getattr(self._bpod, "_write_lock", None)
        if lock is not None:
            with lock:
                yield
        else:
            yield

    def _out(self, channel_name, channel_addr, value) -> None:
        with self._lock():
            self._bpod.manual_override(
                ChannelType.OUTPUT, channel_name, channel_addr, value
            )

    # ------------------------------------------------------------------
    # Valve control
    # ------------------------------------------------------------------

    def open_valve(self, port: int) -> None:
        """Open valve port (1-indexed) indefinitely."""
        self._out(ChannelName.VALVE, port, 1)

    def close_valve(self, port: int) -> None:
        """Close valve port (1-indexed)."""
        self._out(ChannelName.VALVE, port, 0)

    def close_all_valves(self, n_ports: int = 8) -> None:
        """Close all valve ports (defensive cleanup)."""
        with self._lock():
            for port in range(1, n_ports + 1):
                with contextlib.suppress(Exception):
                    self._bpod.manual_override(
                        ChannelType.OUTPUT, ChannelName.VALVE, port, 0
                    )

    def pulse_valve(self, port: int, duration_ms: float, blocking: bool = True) -> None:
        """Open valve for duration_ms milliseconds then close.

        Parameters
        ----------
        port:
            Valve port number (1-indexed).
        duration_ms:
            Pulse duration in milliseconds.
        blocking:
            If True, return only after the pulse completes.
            If False, open the valve and return immediately (caller must close).
        """
        self._out(ChannelName.VALVE, port, 1)
        if blocking:
            time.sleep(duration_ms / 1000.0)
            self._out(ChannelName.VALVE, port, 0)

    # ------------------------------------------------------------------
    # Reward delivery
    # ------------------------------------------------------------------

    def reward(self, port: int, duration_ms: float, blocking: bool = True) -> None:
        """Deliver a single water reward by pulsing valve for duration_ms.

        Equivalent to pulse_valve but named for the semantic use case.
        """
        self.pulse_valve(port, duration_ms, blocking=blocking)

    # ------------------------------------------------------------------
    # PWM (port LEDs / light)
    # ------------------------------------------------------------------

    def set_port_light(self, port: int, pwm: int) -> None:
        """Set PWM brightness for a behaviour port LED.

        Parameters
        ----------
        port:
            Port number (1-indexed).
        pwm:
            Brightness 0–255 (0 = off, 255 = full).
        """
        self._out(ChannelName.PWM, port, pwm)

    # ------------------------------------------------------------------
    # BNC outputs
    # ------------------------------------------------------------------

    def set_bnc(self, channel: int, value: int) -> None:
        """Set a BNC output channel high (1) or low (0).

        Parameters
        ----------
        channel:
            BNC channel number (1-indexed).
        value:
            1 for high, 0 for low.
        """
        self._out(ChannelName.BNC, channel, value)

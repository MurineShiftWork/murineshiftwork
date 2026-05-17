"""Weighing-scale abstraction layer.

Use `make_scale(serial_port)` to get the default serial-scale adapter.
Implement `WeighingScaleBase` to plug in any other hardware.
Pass `scale_type="sim"` (or inject a `SimWeighingScale` directly) for
hardware-free testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class WeighingScaleBase(ABC):
    """Minimal interface every weighing-scale driver must satisfy."""

    @abstractmethod
    def start(self) -> None:
        """Connect and wait until the scale is ready."""

    @abstractmethod
    def tare(self) -> None:
        """Zero the scale at its current reading."""

    @abstractmethod
    def read_weight_blocking(self) -> float:
        """Return current weight in grams, blocking until a stable reading is available."""

    def stop(self) -> None:
        """Disconnect / clean up (optional — not all hardware needs it)."""


class SerialWeighingScaleAdapter(WeighingScaleBase):
    """Wraps `serial_weighing_scale.SerialWeighingScale` behind the shared interface."""

    def __init__(self, serial_port: str) -> None:
        from serial_weighing_scale import SerialWeighingScale

        self._scale = SerialWeighingScale(serial_port=serial_port)

    def start(self) -> None:
        self._scale.start()

    def tare(self) -> None:
        self._scale.tare()

    def read_weight_blocking(self) -> float:
        return self._scale.read_weight_blocking()


class SimWeighingScale(WeighingScaleBase):
    """Simulated scale — returns deterministic synthetic weights.

    Used for hardware-free testing and CI.  Returns a fixed weight_g on every
    call to read_weight_blocking() after a tare, regardless of what the
    simulated Bpod has done (the calibration task just needs a non-zero number
    to complete the µL/drop calculation).

    Attributes tracked for test assertions:
        tare_count  — number of tare() calls
        read_count  — total number of read_weight_blocking() calls
        weight_log  — list of all returned weight values in order
    """

    def __init__(self, weight_g: float = 0.020) -> None:
        self._weight_g = weight_g
        self.tare_count: int = 0
        self.read_count: int = 0
        self.weight_log: list[float] = []

    def start(self) -> None:
        pass

    def tare(self) -> None:
        self.tare_count += 1

    def read_weight_blocking(self) -> float:
        self.read_count += 1
        self.weight_log.append(self._weight_g)
        return self._weight_g

    def stop(self) -> None:
        pass


def make_scale(serial_port: str = "", scale_type: str = "serial") -> WeighingScaleBase:
    """Factory: return the appropriate scale adapter for *scale_type*.

    Supported values:
        ``"serial"`` — :class:`SerialWeighingScaleAdapter` (default, requires hardware)
        ``"sim"``    — :class:`SimWeighingScale` (hardware-free, for testing)
    """
    if scale_type == "serial":
        return SerialWeighingScaleAdapter(serial_port=serial_port)
    if scale_type == "sim":
        return SimWeighingScale()
    raise ValueError(f"Unknown scale_type {scale_type!r}. Supported: 'serial', 'sim'")

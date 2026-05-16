"""Weighing-scale abstraction layer.

Use `make_scale(serial_port)` to get the default serial-scale adapter.
Implement `WeighingScaleBase` to plug in any other hardware.
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


def make_scale(serial_port: str, scale_type: str = "serial") -> WeighingScaleBase:
    """Factory: return the appropriate scale adapter for *scale_type*.

    Currently supported:
        ``"serial"`` — :class:`SerialWeighingScaleAdapter` (default)
    """
    if scale_type == "serial":
        return SerialWeighingScaleAdapter(serial_port=serial_port)
    raise ValueError(
        f"Unknown scale_type {scale_type!r}. Supported: 'serial'"
    )

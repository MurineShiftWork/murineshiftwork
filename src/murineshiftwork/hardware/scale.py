"""Weighing-scale abstraction layer.

Use `make_scale(serial_port, scale_type)` to get a scale adapter.
scale_type: "hx711" (Arduino+HX711), "bench" (RS-232 bench scale), "sim" (testing).
Implement `WeighingScaleBase` to add other hardware.
"""

from __future__ import annotations

import logging
import statistics
import time
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
    """Wraps `serial_scale_hx711.Scale` behind the shared interface."""

    def __init__(self, serial_port: str) -> None:
        from serial_scale_hx711 import Scale

        self._scale = Scale(serial_port=serial_port)

    def start(self) -> None:
        self._scale.start()

    def tare(self) -> None:
        self._scale.tare()

    def read_weight_blocking(
        self,
        n_valid: int = 3,
        inter_read_delay: float = 0.2,
        timeout: float = 30.0,
    ) -> float:
        # hx711 read_weight() logs ERROR on parse failures that are transient and
        # expected (stale serial buffer on first read). Suppress those and retry here
        # with a single WARNING summary so the noise doesn't alarm users.
        hx_log = logging.getLogger("serial_scale_hx711")
        prev_level = hx_log.level
        hx_log.setLevel(logging.CRITICAL)

        readings: list[float] = []
        n_failed = 0
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                val = self._scale.read_weight()
                if val is not None:
                    readings.append(val)
                    if len(readings) >= n_valid:
                        if n_failed:
                            logging.warning(
                                "HX711: %d parse failure(s) before stable read",
                                n_failed,
                            )
                        return statistics.median(readings)
                else:
                    n_failed += 1
                time.sleep(inter_read_delay)
        finally:
            hx_log.setLevel(prev_level)

        raise TimeoutError(
            f"HX711 scale could not produce {n_valid} valid readings within {timeout}s "
            f"({n_failed} parse failures)"
        )


class BenchScaleAdapter(WeighingScaleBase):
    """Wraps `serial_scale_bench.Scale` (RS-232/USB bench scale) behind the shared interface."""

    def __init__(self, serial_port: str, baudrate: int = 9600) -> None:
        from serial_scale_bench import Scale

        self._scale = Scale(serial_port=serial_port, baudrate=baudrate)

    def start(self) -> None:
        self._scale.start()

    def tare(self) -> None:
        self._scale.tare()

    def read_weight_blocking(self) -> float:
        return self._scale.read_weight_blocking()

    def stop(self) -> None:
        self._scale.disconnect()


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


def make_scale(
    serial_port: str = "",
    scale_type: str = "hx711",
    baudrate: int | None = None,
) -> WeighingScaleBase:
    """Factory: return the appropriate scale adapter for *scale_type*.

    Supported values:
        ``"hx711"`` — :class:`SerialWeighingScaleAdapter` (Arduino+HX711, default)
        ``"bench"`` — :class:`BenchScaleAdapter` (RS-232/USB commercial scale)
        ``"sim"``   — :class:`SimWeighingScale` (hardware-free, for testing)
    """
    if scale_type == "hx711":
        return SerialWeighingScaleAdapter(serial_port=serial_port)
    if scale_type == "bench":
        return BenchScaleAdapter(serial_port=serial_port, baudrate=baudrate or 9600)
    if scale_type == "sim":
        return SimWeighingScale()
    raise ValueError(
        f"Unknown scale_type {scale_type!r}. Supported: 'hx711', 'bench', 'sim'"
    )

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.optimize import curve_fit as _scipy_curve_fit


# ---------------------------------------------------------------------------
# Serial devices

class SerialDevice(BaseModel):
    type: str
    port_by_path: str

    def resolve_port(self) -> str:
        """Resolve port_by_path → /dev/ttyXXX (Linux; raises ValueError if absent)."""
        p = Path(f"/dev/serial/by-path/{self.port_by_path}")
        if not p.exists():
            raise ValueError(
                f"Serial device not found: /dev/serial/by-path/{self.port_by_path}"
            )
        return str(p.resolve())


class BpodDevice(SerialDevice):
    type: Literal["bpod"]


class PulsePalDevice(SerialDevice):
    type: Literal["pulsepal"]


class AxisConfig(BaseModel):
    id: int
    position_min: int = 1
    position_max: int = 999
    velocity_max: int = 200
    operating_mode: str = "OP_POSITION"


class StageTowerDevice(SerialDevice):
    type: Literal["stage_tower"]
    baudrate: int = 115200
    timeout: float = 0.1
    axes: dict[str, AxisConfig] = {}
    known_positions: dict[str, dict[str, Any]] = {}


class GenericSerialDevice(SerialDevice):
    type: Literal["serial_generic"]


DeviceUnion = Annotated[
    Union[BpodDevice, PulsePalDevice, StageTowerDevice, GenericSerialDevice],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Calibrations

def _exp_model(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """a * exp(b * x) + c  — the valve volume-vs-time model."""
    return a * np.exp(b * x) + c


class ValveCalibration(BaseModel):
    """Bpod valve calibration: list of [open_time_s, delivered_ul] pairs.

    Volume delivered by a solenoid valve grows exponentially with opening time:
        volume_ul = a * exp(b * open_time_s) + c
    All lookup methods fit this model to the stored points on demand.
    """

    updated: str = ""
    points: list[list[float]] = []

    def _fit(self) -> tuple[float, float, float]:
        """Fit the exponential model to stored points. Returns (a, b, c).

        Initial guesses are derived from the data so curve_fit converges reliably
        even with sparse calibration sets (≥ 3 points).
        """
        pts = sorted(self.points, key=lambda p: p[0])
        s = np.array([p[0] for p in pts], dtype=float)
        ul = np.array([p[1] for p in pts], dtype=float)

        ul_min, ul_max = ul.min(), ul.max()
        s_span = s.max() - s.min()
        b0 = np.log(ul_max / ul_min) / s_span if s_span > 0 and ul_min > 0 else 20.0
        a0 = ul_min
        c0 = 0.0

        try:
            popt, _ = _scipy_curve_fit(
                _exp_model,
                s, ul,
                p0=[a0, b0, c0],
                bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), float(popt[2])
        except RuntimeError as exc:
            raise ValueError(
                f"Exponential fit failed — check calibration points for valve.\n{exc}"
            )

    def ul_for_s(self, open_s: float) -> float:
        a, b, c = self._fit()
        return float(_exp_model(np.array([open_s]), a, b, c)[0])

    def s_for_ul(self, volume_ul: float) -> float:
        """Invert the exponential fit numerically via dense sampling.

        Sampling is used rather than the analytical inverse (ln((v-c)/a)/b) because
        the analytical form is numerically fragile when a or b are near zero.
        """
        pts = sorted(self.points, key=lambda p: p[0])
        s_min, s_max = pts[0][0], pts[-1][0]
        s_dense = np.linspace(s_min, s_max, 2000)
        a, b, c = self._fit()
        ul_dense = _exp_model(s_dense, a, b, c)
        return float(np.interp(volume_ul, ul_dense, s_dense))

    def validate(self, r2_threshold: float = 0.95) -> tuple[bool, str]:
        """Return (is_valid, reason).

        Checks:
        - At least 3 calibration points
        - All volumes positive
        - Volume monotonically increases with open time
        - Exponential R² ≥ r2_threshold
        - Fit parameter b > 0 (growth, not decay)
        """
        if len(self.points) < 3:
            return False, f"only {len(self.points)} point(s) — need at least 3"

        pts = sorted(self.points, key=lambda p: p[0])
        s = np.array([p[0] for p in pts], dtype=float)
        ul = np.array([p[1] for p in pts], dtype=float)

        if np.any(ul <= 0):
            return False, "one or more volume values are ≤ 0"
        if np.any(np.diff(ul) <= 0):
            return False, "volume is not monotonically increasing with open time"

        try:
            a, b, c = self._fit()
        except ValueError as exc:
            return False, str(exc)

        if b <= 0:
            return False, f"fit parameter b = {b:.4f} ≤ 0 (curve is not exponential growth)"

        ul_pred = _exp_model(s, a, b, c)
        ss_res = float(np.sum((ul - ul_pred) ** 2))
        ss_tot = float(np.sum((ul - ul.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        if r2 < r2_threshold:
            return False, f"R² = {r2:.3f} < {r2_threshold} (poor exponential fit)"

        return True, f"ok (R² = {r2:.3f}, a={a:.4f}, b={b:.5f}, c={c:.4f})"


class Calibrations(BaseModel):
    bpod_valve: dict[str, ValveCalibration] = {}


# ---------------------------------------------------------------------------
# Camera config (minimal — full spec in design/camera_acquisition.md)

class CameraConfig(BaseModel):
    backend: str = "rce"    # "rce" | "flir_bonsai"
    config: str = ""        # path to backend-specific config file


# ---------------------------------------------------------------------------
# Setup config

class SetupConfig(BaseModel):
    name: str
    devices: dict[str, DeviceUnion] = {}
    cameras: Optional[CameraConfig] = None
    calibrations: Calibrations = Calibrations()

    def device_port(self, device_name: str) -> str:
        if device_name not in self.devices:
            raise KeyError(f"Device '{device_name}' not in setup '{self.name}'")
        return self.devices[device_name].resolve_port()

    def valve_ul_for_s(self, port: str | int, open_s: float) -> float:
        return self.calibrations.bpod_valve[str(port)].ul_for_s(open_s)

    def valve_s_for_ul(self, port: str | int, volume_ul: float) -> float:
        return self.calibrations.bpod_valve[str(port)].s_for_ul(volume_ul)


# ---------------------------------------------------------------------------
# Subject config

class SubjectConfig(BaseModel):
    name: str
    registered: str = ""
    project: str = ""
    experiment: str = ""
    comment: str = ""
    aliases: list[str] = []
    task_overrides: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Execution config — assembled at session start from setup + subject + task

class ExecutionConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    setup: Optional[SetupConfig] = None
    subject: Optional[SubjectConfig] = None
    task_name: str = ""
    task_settings: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Hardware action request — same shape used by Phase 1 CLI and Phase 2 RPC

class ActionRequest(BaseModel):
    """Describes a one-shot hardware action to execute on a named setup device.

    Fields map directly to the Phase 2 FastAPI body so the CLI can slot into
    the same dispatch path without changes when ControllerSession is introduced.
    """
    setup: str
    device: str
    action: str
    params: dict[str, Any] = {}

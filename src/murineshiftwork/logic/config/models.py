from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any, Literal

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


class ScaleDevice(SerialDevice):
    type: Literal["scale"]
    scale_type: Literal["hx711", "bench"] = "hx711"
    baudrate: int = 9600


DeviceUnion = Annotated[
    BpodDevice | PulsePalDevice | StageTowerDevice | GenericSerialDevice | ScaleDevice,
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

        # Drop dead-zone / noise points (≤ 0 µL) before fitting so they don't
        # corrupt the initial-guess calculation or pull the optimizer to b ≈ 0.
        mask = ul > 0
        s, ul = s[mask], ul[mask]

        if len(s) < 3:
            raise ValueError(
                f"Too few positive-volume calibration points ({len(s)}) after "
                "filtering dead-zone measurements — need at least 3."
            )

        ul_min, ul_max = float(ul.min()), float(ul.max())
        s_span = float(s.max() - s.min())
        b0 = np.log(ul_max / ul_min) / s_span if s_span > 0 and ul_min > 0 else 5.0
        a0 = ul_min
        c0 = 0.0

        try:
            popt, _ = _scipy_curve_fit(
                _exp_model,
                s,
                ul,
                p0=[a0, b0, c0],
                bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]),
                maxfev=10_000,
            )
            return float(popt[0]), float(popt[1]), float(popt[2])
        except RuntimeError as exc:
            raise ValueError(
                f"Exponential fit failed — check calibration points for valve.\n{exc}"
            )

    def _calibrated_range_ul(self) -> tuple[float, float]:
        """Return (min_ul, max_ul) of the calibrated volume range."""
        pts = sorted(self.points, key=lambda p: p[0])
        a, b, c = self._fit()
        ul_min = float(_exp_model(np.array([pts[0][0]]), a, b, c)[0])
        ul_max = float(_exp_model(np.array([pts[-1][0]]), a, b, c)[0])
        return ul_min, ul_max

    def ul_for_s(self, open_s: float) -> float:
        pts = sorted(self.points, key=lambda p: p[0])
        s_min, s_max = pts[0][0], pts[-1][0]
        if open_s < s_min or open_s > s_max:
            logging.warning(
                "ValveCalibration.ul_for_s: open_s=%.4f s is outside calibrated "
                "range [%.4f, %.4f] s — extrapolating",
                open_s,
                s_min,
                s_max,
            )
        a, b, c = self._fit()
        return float(_exp_model(np.array([open_s]), a, b, c)[0])

    def s_for_ul(self, volume_ul: float) -> float:
        """Invert the exponential fit numerically via dense sampling.

        Sampling is used rather than the analytical inverse (ln((v-c)/a)/b) because
        the analytical form is numerically fragile when a or b are near zero.

        The sample grid extends 50% beyond the calibrated time range so that
        requests outside the calibrated volume range extrapolate via the fit
        model rather than clamping silently at the boundary.
        """
        pts = sorted(self.points, key=lambda p: p[0])
        s_min, s_max = pts[0][0], pts[-1][0]
        margin = (s_max - s_min) * 0.5
        s_dense = np.linspace(max(0.0, s_min - margin), s_max + margin, 4000)
        a, b, c = self._fit()
        ul_dense = _exp_model(s_dense, a, b, c)
        ul_lo, ul_hi = float(ul_dense.min()), float(ul_dense.max())
        if volume_ul < ul_lo or volume_ul > ul_hi:
            logging.warning(
                "ValveCalibration.s_for_ul: %.3f µL is outside calibrated "
                "range [%.3f, %.3f] µL — extrapolating",
                volume_ul,
                ul_lo,
                ul_hi,
            )
        return float(np.interp(volume_ul, ul_dense, s_dense))

    def validate(self, r2_threshold: float = 0.95) -> tuple[bool, str]:  # type: ignore[override]
        """Return (is_valid, reason).

        Checks:
        - At least 3 calibration points
        - All volumes positive
        - Volume monotonically increases with open time
        - Exponential R² ≥ r2_threshold
        - Fit parameter b > 0 (growth, not decay)
        """
        pts = sorted(self.points, key=lambda p: p[0])
        s = np.array([p[0] for p in pts], dtype=float)
        ul = np.array([p[1] for p in pts], dtype=float)

        # Filter dead-zone points (same as _fit does) before any checks.
        mask = ul > 0
        s, ul = s[mask], ul[mask]

        if len(s) < 3:
            return (
                False,
                f"only {int(mask.sum())} positive-volume point(s) — need at least 3",
            )

        if np.any(np.diff(ul) <= 0):
            bad = int(np.argmax(np.diff(ul) <= 0)) + 1
            return (
                False,
                f"volume not monotonically increasing: point {bad} breaks order",
            )

        try:
            a, b, c = self._fit()
        except ValueError as exc:
            return False, str(exc)

        if b <= 0:
            return (
                False,
                f"fit parameter b = {b:.4f} ≤ 0 (curve is not exponential growth)",
            )

        ul_pred = _exp_model(s, a, b, c)
        ss_res = float(np.sum((ul - ul_pred) ** 2))
        ss_tot = float(np.sum((ul - ul.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        if r2 < r2_threshold:
            return (
                False,
                f"R² = {r2:.3f} < {r2_threshold} (poor exponential fit)",
            )

        return True, f"ok (R² = {r2:.3f}, a={a:.4f}, b={b:.5f}, c={c:.4f})"


class Calibrations(BaseModel):
    bpod_valve: dict[str, ValveCalibration] = {}
    stale_days: int = 180


# ---------------------------------------------------------------------------
# Camera config


class CameraUnit(BaseModel):
    """Per-camera specification for the FLIR/Bonsai backend."""

    index: int
    fps: int = 60


class CameraConfig(BaseModel):
    backend: str = "rce"  # "rce" | "flir_bonsai"
    config: str = ""  # RCE only: path to ensemble YAML
    # FLIR/Bonsai-specific (ignored when backend="rce")
    driver: str = "flycap"  # "flycap" | "spinnaker"
    bonsai_exe: str = ""  # path to Bonsai.exe; falls back to BONSAI_EXE env var
    workflow: str = ""  # workflow stem; auto-derived as run-flir-{driver}-1cam if empty
    cameras: list[CameraUnit] = []  # per-camera index + fps; preferred over n_cameras
    # Flat shorthand (used when cameras list is empty)
    n_cameras: int = 1
    fps: int = 60  # ignored for spinnaker (set in workflow XML)


# ---------------------------------------------------------------------------
# Hook config — lists of dotted import paths for pre/post session hooks


class HooksConfig(BaseModel):
    pre_task: list[str] = []
    post_task: list[str] = []


# ---------------------------------------------------------------------------
# Setup config


class SetupConfig(BaseModel):
    name: str
    devices: dict[str, DeviceUnion] = {}
    cameras: CameraConfig | None = None
    calibrations: Calibrations = Calibrations()
    hooks: HooksConfig = HooksConfig()
    open_ephys_url: str = ""

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

SUBJECT_CONFIG_SCHEMA_VERSION = 1


class SubjectConfig(BaseModel):
    schema_version: int = 1
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

    setup: SetupConfig | None = None
    subject: SubjectConfig | None = None
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

"""PulsePal stimulation wrapper using pypulsepal.

Supports optional laser power control via Doric LDFL5 (0-5V analog input).
Set laser_power=None (default) for fixed 5V TTL output; 0.0-1.0 for Doric power mapping.

Channel indices are 0-based throughout (pypulsepal native).
Output channels: 0-3 (firmware channels 1-4).
Trigger channels: 0-1 (firmware trigger inputs 1-2).
"""

import logging
import math
import time
from typing import Any, ClassVar

from numpy import zeros

try:
    from pypulsepal import PulsePal as _PulsePal
except ImportError as _e:
    raise ImportError(
        "pypulsepal is required for stimulation. Install with: pip install pypulsepal"
    ) from _e


# Doric LDFL5: single BNC input, 0-5V analog/TTL combined.
DORIC_CURRENT_SENSITIVITY = 80.0  # mA per volt (from manual spec)
DORIC_MAX_CURRENT_MA = 120.0  # mA — specific laser diode max
DORIC_MAX_VOLTAGE = DORIC_MAX_CURRENT_MA / DORIC_CURRENT_SENSITIVITY

WAVEFORM_LINEAR = "linear"
WAVEFORM_SINE = "sine"
WAVEFORM_RAISED_COSINE = "raised_cosine"
_PULSEPAL_SAMPLE_RATE = 20000  # 50 us per cycle


def power_to_voltage(laser_power: float) -> float:
    """Map 0.0-1.0 power fraction to volts for Doric LDFL5_450_0.75."""
    return round(float(laser_power) * DORIC_MAX_VOLTAGE, 4)


def _ramp_envelope(n_samples: int, ramp_type: str, rising: bool) -> list[float]:
    """Normalized [0,1] ramp of length n_samples. rising=False returns the mirror (1 down to 0)."""
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [1.0]
    t = [i / (n_samples - 1) for i in range(n_samples)]
    if ramp_type == WAVEFORM_LINEAR:
        vals = t
    elif ramp_type == WAVEFORM_SINE:
        vals = [math.sin(math.pi / 2 * x) for x in t]
    elif ramp_type == WAVEFORM_RAISED_COSINE:
        vals = [(1 - math.cos(math.pi * x)) / 2 for x in t]
    else:
        raise ValueError(
            f"Unknown waveform type {ramp_type!r}; valid: linear, sine, raised_cosine"
        )
    return vals if rising else list(reversed(vals))


def generate_waveform_voltages(
    target_voltage: float,
    on_ramp_type: str | None,
    on_ramp_duration_s: float,
    center_duration_s: float,
    off_ramp_type: str | None,
    off_ramp_duration_s: float,
    sample_rate: int = _PULSEPAL_SAMPLE_RATE,
) -> tuple[list[float], float]:
    """Build shaped-pulse voltage samples for PulsePal custom waveform upload.

    Three phases: on-ramp (0 to target), flat center (target), off-ramp (target to 0).
    Any phase can be zero duration. Set center_duration_s=0 with matching ramps to get
    a pure bump with no flat top.

    Returns (voltage_samples, total_duration_s).
    """
    dt = 1.0 / sample_rate
    n_on = round(on_ramp_duration_s * sample_rate) if on_ramp_type else 0
    n_center = round(center_duration_s * sample_rate)
    n_off = round(off_ramp_duration_s * sample_rate) if off_ramp_type else 0

    samples = (
        (
            [
                v * target_voltage
                for v in _ramp_envelope(n_on, on_ramp_type, rising=True)
            ]
            if on_ramp_type
            else []
        )
        + [target_voltage] * n_center
        + (
            [
                v * target_voltage
                for v in _ramp_envelope(n_off, off_ramp_type, rising=False)
            ]
            if off_ramp_type
            else []
        )
    )
    return samples, len(samples) * dt


class Stimulation:
    pulsePal: Any = None
    port = ""

    # Size 4: one entry per output channel (0-indexed, matching pypulsepal).
    channels_inactive = zeros(4).astype("int")
    channels_stimulation = channels_inactive.copy()
    channels_ttl_copy = channels_inactive.copy()

    time_of_last_activation = 0

    _DEFAULT_IN_DICT: ClassVar[dict[str, Any]] = {
        "pulse_duration": 0.005,
        "pulse_frequency": 30,
        "pulse_train_duration": 10,
        "pulse_train_delay": 0,
        "trigger_channels_for_stimulation": [0],
        "channels_stimulation": [2],
        "channels_ttl_copy": [],
        "reset_stimulation_after_sec": 0.005,
        "laser_power": None,  # None → fixed 5V; 0.0–1.0 → Doric LDFL5 power mapping
    }

    in_dict: dict[str, Any]
    test = 0
    channels_currently_active: list[Any] = []
    emergency_off_bool = False

    def __init__(self, port=None, in_dict: dict | None = None, test: bool = False):
        self.test = test
        self.port = port
        self._channel_params: dict = {}
        self.in_dict = dict(self._DEFAULT_IN_DICT)
        for k, v in (in_dict or {}).items():
            self.in_dict[k] = v

        self._waveform_on_ramp_type: str | None = self.in_dict.pop(
            "waveform_on_ramp_type", None
        )
        self._waveform_on_ramp_duration_s: float = float(
            self.in_dict.pop("waveform_on_ramp_duration_s", 0.0)
        )
        self._waveform_center_duration_s: float = float(
            self.in_dict.pop("waveform_center_duration_s", 0.0)
        )
        self._waveform_off_ramp_type: str | None = self.in_dict.pop(
            "waveform_off_ramp_type", None
        )
        self._waveform_off_ramp_duration_s: float = float(
            self.in_dict.pop("waveform_off_ramp_duration_s", 0.0)
        )
        self._use_custom_waveform: bool = bool(
            self._waveform_on_ramp_type or self._waveform_off_ramp_type
        )

        if self._use_custom_waveform:
            _, total_s = generate_waveform_voltages(
                target_voltage=1.0,
                on_ramp_type=self._waveform_on_ramp_type,
                on_ramp_duration_s=self._waveform_on_ramp_duration_s,
                center_duration_s=self._waveform_center_duration_s,
                off_ramp_type=self._waveform_off_ramp_type,
                off_ramp_duration_s=self._waveform_off_ramp_duration_s,
            )
            cycle_s = 1.0 / float(self.in_dict.get("pulse_frequency", 30))
            if total_s > cycle_s:
                raise ValueError(
                    f"Waveform duration {total_s * 1000:.2f} ms exceeds pulse cycle "
                    f"{cycle_s * 1000:.2f} ms (1/pulse_frequency). "
                    "Reduce ramp/center durations or lower pulse_frequency."
                )
            self.in_dict["pulse_duration"] = total_s

        laser_power = self.in_dict.get("laser_power")
        if laser_power is not None:
            self._validate_power(laser_power)

        self.channels_stimulation = self.channels_inactive.copy()
        self.channels_ttl_copy = self.channels_inactive.copy()

        for channel in self.in_dict["channels_stimulation"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                pulse_frequency=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
                laser_power=laser_power,
            )
            self.channels_stimulation[int(channel)] = 1

        for channel in self.in_dict["channels_ttl_copy"]:
            # Mirrors stim pulse params at full 5V for ephys digital input
            # (BNC2110 threshold ~2V; modulated stim voltage is sub-threshold at low power).
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                pulse_frequency=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
                laser_power=None,  # always 5V
            )
            self.channels_ttl_copy[int(channel)] = 1

    @staticmethod
    def _validate_power(laser_power: float) -> None:
        if not (0.0 <= laser_power <= 1.0):
            raise ValueError(
                f"laser_power must be in [0.0, 1.0], got {laser_power}. "
                f"Maps to 0–{DORIC_MAX_VOLTAGE:.3f}V (0–{DORIC_MAX_CURRENT_MA}mA) "
                f"on Doric LDFL5_450_0.75 at {DORIC_CURRENT_SENSITIVITY}mA/V."
            )

    def _set_channel_params(
        self,
        channel=0,
        isBiphasic=0,
        laser_power=None,
        restingVoltage=0,
        phase1Duration=0.005,
        pulse_frequency=0.05,
        pulseTrainDuration=3000.0,
        pulseTrainDelay=0.0,
    ):
        phase1Voltage = power_to_voltage(laser_power) if laser_power is not None else 5
        ipi = 1 / float(pulse_frequency)
        self._channel_params[channel] = {
            "isBiphasic": isBiphasic,
            "phase1Voltage": phase1Voltage,
            "restingVoltage": restingVoltage,
            "phase1Duration": round(float(phase1Duration), 6),
            "interPulseInterval": round(ipi - phase1Duration, 6),
            "pulseTrainDuration": float(pulseTrainDuration),
            "pulseTrainDelay": round(float(pulseTrainDelay), 3),
        }

    def set_power(self, laser_power: float, sync: bool = True) -> None:
        """Update laser power (0.0–1.0) without changing timing params."""
        self._validate_power(laser_power)
        self.in_dict["laser_power"] = laser_power
        phase1Voltage = power_to_voltage(laser_power)
        for channel in self.in_dict["channels_stimulation"]:
            if self.pulsePal is not None and sync:
                self.pulsePal.program_one_param(
                    channel=int(channel),
                    param_name="phase1Voltage",
                    param_value=phase1Voltage,
                )
            if channel in self._channel_params:
                self._channel_params[channel]["phase1Voltage"] = phase1Voltage
            logging.info(
                f"PulsePal: Ch{channel} power set to {laser_power:.2f} "
                f"({phase1Voltage:.3f}V on Doric LDFL5 input)"
            )

    def set_pulse_params(
        self,
        pulse_duration: float | None = None,
        pulse_frequency: float | None = None,
        pulse_train_duration: float | None = None,
        laser_power: float | None = None,
        sync: bool = True,
    ) -> None:
        """Update any combination of timing + power params between protocols."""
        if laser_power is not None:
            self._validate_power(laser_power)
            self.in_dict["laser_power"] = laser_power
        if pulse_duration is not None:
            self.in_dict["pulse_duration"] = pulse_duration
        if pulse_frequency is not None:
            self.in_dict["pulse_frequency"] = pulse_frequency
        if pulse_train_duration is not None:
            self.in_dict["pulse_train_duration"] = pulse_train_duration

        for channel in self.in_dict["channels_stimulation"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                pulse_frequency=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
                laser_power=self.in_dict.get("laser_power"),
            )
            if self.pulsePal is not None and sync:
                for param_name, value in self._channel_params[int(channel)].items():
                    self.pulsePal.program_one_param(
                        channel=int(channel),
                        param_name=param_name,
                        param_value=value,
                    )

    def setup_custom_waveform(self, slot: int = 0) -> float:
        """Upload shaped waveform to PulsePal and configure stim channels to use it.

        Call after connect(). No-op if no waveform params were set.
        Returns total waveform duration in seconds (0 if no waveform).
        """
        if not self._use_custom_waveform:
            return 0.0

        first_ch = int(self.in_dict["channels_stimulation"][0])
        target_v = self._channel_params[first_ch]["phase1Voltage"]

        voltages, total_s = generate_waveform_voltages(
            target_voltage=target_v,
            on_ramp_type=self._waveform_on_ramp_type,
            on_ramp_duration_s=self._waveform_on_ramp_duration_s,
            center_duration_s=self._waveform_center_duration_s,
            off_ramp_type=self._waveform_off_ramp_type,
            off_ramp_duration_s=self._waveform_off_ramp_duration_s,
        )

        # Pad waveform to exactly one pulse cycle with trailing zeros.
        # customTrainLoop=1 then repeats the full cycle (pulse + silence) at
        # pulse_frequency during the gate — set_continuous alone does not repeat
        # custom waveform channels.
        pulse_frequency = float(self.in_dict.get("pulse_frequency", 30))
        n_cycle = round(_PULSEPAL_SAMPLE_RATE / pulse_frequency)
        n_pad = max(0, n_cycle - len(voltages))
        padded_voltages = voltages + [0.0] * n_pad

        self.pulsePal.upload_custom_waveform(
            pulse_train_id=slot,
            pulse_width=1.0 / _PULSEPAL_SAMPLE_RATE,
            pulse_voltages=padded_voltages,
        )

        _pulse_width = 1.0 / _PULSEPAL_SAMPLE_RATE
        for ch in self.in_dict["channels_stimulation"]:
            ch = int(ch)
            # Each waveform sample must last exactly one sample period; the gap
            # between repetitions is the trailing zero-padding in padded_voltages.
            self.pulsePal.program_one_param(ch, "phase1Duration", _pulse_width)
            self.pulsePal.program_one_param(ch, "interPulseInterval", 0.0)
            self.pulsePal.program_one_param(ch, "customTrainID", slot + 1)
            self.pulsePal.program_one_param(ch, "customTrainTarget", 0)
            self.pulsePal.program_one_param(ch, "customTrainLoop", 1)
            if self.in_dict.get("trigger_mode") == "gated":
                # Prevent pulseTrainDuration from expiring mid-gate; gate-low is the
                # only stop signal. 3600 s is safe for any realistic session.
                self.pulsePal.program_one_param(ch, "pulseTrainDuration", 3600.0)

        logging.info(
            "PulsePal: waveform slot %d — %d samples / %.2f ms "
            "(on %s %.1f ms | center %.1f ms | off %s %.1f ms)",
            slot,
            len(voltages),
            total_s * 1000,
            self._waveform_on_ramp_type or "none",
            self._waveform_on_ramp_duration_s * 1000,
            self._waveform_center_duration_s * 1000,
            self._waveform_off_ramp_type or "none",
            self._waveform_off_ramp_duration_s * 1000,
        )
        return total_s

    def _sync_channel_configs(self) -> None:
        """Write _channel_params into pulsePal.channel_configs and unlink inactive channels."""
        for cfg in self.pulsePal.channel_configs:
            cfg.linkTriggerChannel1 = False
            cfg.linkTriggerChannel2 = False
        for ch, params in self._channel_params.items():
            cfg = self.pulsePal.channel_configs[ch]
            for k, v in params.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

    def connect(self, handle=None):
        self._owns_connection = handle is None
        if handle is None:
            self.pulsePal = _PulsePal(serial_port=self.port)
            for channel, params in self._channel_params.items():
                for param_name, value in params.items():
                    self.pulsePal.program_one_param(
                        channel=channel,
                        param_name=param_name,
                        param_value=value,
                    )
        else:
            self.pulsePal = handle
            self._sync_channel_configs()
            self.pulsePal.sync_all_params()

        self.off()

        _gated = self.in_dict.get("trigger_mode") == "gated"
        _cont_state = 1 if (_gated or self.in_dict.get("continuous")) else 0
        for channel in list(self.in_dict["channels_stimulation"]) + list(
            self.in_dict["channels_ttl_copy"]
        ):
            self.pulsePal.set_continuous(channel=int(channel), state=_cont_state)

        # Set trigger links: 1 only for active channels, 0 for all others.
        for trigger_ch in self.in_dict["trigger_channels_for_stimulation"]:
            if trigger_ch not in (0, 1):
                continue
            link_param = f"linkTriggerChannel{trigger_ch + 1}"
            for out_ch in range(self.pulsePal.nr_output_channels):
                active = bool(
                    self.channels_stimulation[out_ch] or self.channels_ttl_copy[out_ch]
                )
                try:
                    self.pulsePal.program_one_param(
                        channel=out_ch,
                        param_name=link_param,
                        param_value=1 if active else 0,
                    )
                except Exception as exc:
                    logging.warning(
                        "PulsePal: could not set %s for ch %d: %s",
                        link_param,
                        out_ch,
                        exc,
                    )
            if "trigger_mode" in self.in_dict and self.in_dict["trigger_mode"] in (
                "normal",
                "toggle",
                "gated",
            ):
                self.pulsePal.program_trigger_channel(
                    trigger_channel=trigger_ch,
                    trigger_mode=self.in_dict["trigger_mode"],
                )

        logging.info(
            "PulsePal: configured via injected handle"
            if not self._owns_connection
            else f"PulsePal: connected on {self.port}"
        )

    def on(self):
        if not self.emergency_off_bool:
            ch = self.channels_stimulation
            self.pulsePal.trigger_selected_channels(
                channel_1=bool(ch[0]) if len(ch) > 0 else False,
                channel_2=bool(ch[1]) if len(ch) > 1 else False,
                channel_3=bool(ch[2]) if len(ch) > 2 else False,
                channel_4=bool(ch[3]) if len(ch) > 3 else False,
            )
            self.channels_currently_active = self.channels_stimulation
            self.time_of_last_activation = time.time()
        else:
            raise RuntimeError("Stimulation module is in emergency-off state.")

    def off(self):
        if self.pulsePal is not None:
            self.pulsePal.stop_all_outputs()
            self.channels_currently_active = self.channels_inactive

    def _check_channels_active_reset(self):
        if (
            abs(self.time_of_last_activation - time.time())
            >= self.in_dict["reset_stimulation_after_sec"]
        ):
            self.channels_currently_active = self.channels_inactive

    def disconnect(self):
        if self.pulsePal is not None:
            try:
                self.pulsePal.stop_all_outputs()
                if getattr(self, "_owns_connection", True):
                    self.pulsePal.save_settings()
            except Exception:
                pass
            if getattr(self, "_owns_connection", True):
                self.pulsePal = None
        logging.info("PulsePal: disconnected.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def emergency_off(self):
        self.off()
        self.emergency_off_bool = True

    def is_open(self) -> bool:
        try:
            if self.pulsePal is None:
                return False
            return self.pulsePal._arcom.serial_object.is_open  # type: ignore[union-attr]
        except Exception:
            logging.debug("Cannot check if PulsePal is connected.")
            return False

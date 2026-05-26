"""PulsePal stimulation wrapper using pypulsepal.

Supports optional laser power control via Doric LDFL5 (0-5V analog input).
Set laser_power=None (default) for fixed 5V TTL output; 0.0-1.0 for Doric power mapping.

Channel indices are 0-based throughout (pypulsepal native).
Output channels: 0–3 (firmware channels 1–4).
Trigger channels: 0–1 (firmware trigger inputs 1–2).
"""

import logging
import time
from typing import Any, ClassVar

from numpy import zeros

try:
    from pypulsepal import PulsePal as _PulsePal
except ImportError as _e:
    raise ImportError(
        "pypulsepal is required for stimulation. Install with: pip install pypulsepal"
    ) from _e


allowed_trigger_modes = {
    "normal": 0,
    "toggle": 1,
    "gated": 2,
}

# Doric LDFL5: single BNC input, 0-5V analog/TTL combined.
DORIC_CURRENT_SENSITIVITY = 80.0  # mA per volt (from manual spec)
DORIC_MAX_CURRENT_MA = 120.0  # mA — specific laser diode max
DORIC_MAX_VOLTAGE = DORIC_MAX_CURRENT_MA / DORIC_CURRENT_SENSITIVITY


def power_to_voltage(laser_power: float) -> float:
    """Map 0.0–1.0 power fraction to volts for Doric LDFL5_450_0.75."""
    return round(float(laser_power) * DORIC_MAX_VOLTAGE, 4)


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
            "phase1Duration": round(float(phase1Duration), 3),
            "interPulseInterval": round(ipi - phase1Duration, 3),
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

        # Gated trigger mode requires continuous=1 so the pulse train repeats for the
        # full gate duration. The config `continuous` flag still controls non-gated modes.
        _gated = self.in_dict.get("trigger_mode") == "gated"
        for channel in self.in_dict["channels_stimulation"]:
            self.pulsePal.set_continuous(
                channel=int(channel),
                state=1 if (_gated or self.in_dict.get("continuous")) else 0,
            )

        # Set trigger links: 1 only for active stimulation channels, 0 for all others.
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
            if (
                "trigger_mode" in self.in_dict
                and self.in_dict["trigger_mode"] in allowed_trigger_modes
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

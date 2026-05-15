"""Code written by Lars B. Rollik 2021. Updated for laser power control."""
import logging
import time

from numpy import zeros

from murineshiftwork.external.PulsePal3 import PulsePalObject

allowed_trigger_modes = {
    "normal": 0,
    "toggle": 1,
    "gated": 2,
}

# Doric LDFL5: single BNC input, 0-5V analog/TTL combined.
# phase1Voltage = laser_power * DORIC_MAX_VOLTAGE sets output power.
DORIC_MAX_VOLTAGE = 5.0

# Doric LDFL5_450_0.75 - max(I) = 110mA -> 1.375V ~ 100%
# DORIC LDFLS_473 - max(I) = 120mA -> 1.5V ~ 100%
DORIC_CURRENT_SENSITIVITY = 80.0  # mA per volt (from manual spec)
DORIC_MAX_CURRENT_MA = 120.0  # mA - your specific laser diode max

# Derived — DO NOT exceed this voltage
DORIC_MAX_VOLTAGE = DORIC_MAX_CURRENT_MA / DORIC_CURRENT_SENSITIVITY  # = voltage for 100% driver current


def power_to_voltage(laser_power: float) -> float:
    """Map 0.0–1.0 power fraction to volts for Doric LDFL5_450_0.75.

    1.0 → 1.375V → 110mA → rated max output
    0.0 → 0.000V → 0mA  → off

    PulsePal 12-bit DAC: ~0.34mV resolution, so ~0.027mA current steps.
    """
    return round(float(laser_power) * DORIC_MAX_VOLTAGE, 4)


class Stimulation:
    pulsePal = None
    port = ""

    channels_inactive = zeros(5).astype("int")
    channels_stimulation = channels_inactive.copy()
    channels_clock_trigger = channels_inactive.copy()

    time_of_last_activation = 0

    in_dict = {
        "pulse_duration": 0.005,
        "pulse_frequency": 30,
        "pulse_train_duration": 10,
        "pulse_train_delay": 0,
        "trigger_channels_for_stimulation": [1],
        "channels_stimulation": [3],
        "channel_trigger_clock": [4],
        "reset_stimulation_after_sec": 0.005,
        "laser_power": 1.0,  # 0.0 - 1.0, scales phase1Voltage linearly
    }

    test = 0
    channels_currently_active = []
    emergency_off_bool = False

    def __init__(self, port: None, in_dict: dict, test: bool = False):
        self.test = test
        self.pulsePal = PulsePalObject()
        self.port = port

        for k, v in in_dict.items():
            self.in_dict[k] = v

        self._validate_power(self.in_dict["laser_power"])

        for channel in self.in_dict["channels_stimulation"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                pulse_frequency=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
                laser_power=float(self.in_dict["laser_power"]),
            )
            self.channels_stimulation[int(channel)] = 1

        for channel in self.in_dict["channel_trigger_clock"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=0.005,
                pulse_frequency=1,
                pulseTrainDuration=0.005,
                pulseTrainDelay=0,
                laser_power=1.0,  # clock channel always full TTL
            )
            self.channels_clock_trigger[int(channel)] = 1

    @staticmethod
    def _validate_power(laser_power: float):
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
            laser_power=1.0,  # <-- replaces hardcoded phase1Voltage=5
            restingVoltage=0,
            phase1Duration=0.005,
            pulse_frequency=0.05,
            pulseTrainDuration=3000.0,
            pulseTrainDelay=0.0,
    ):
        phase1Voltage = round(float(laser_power) * DORIC_MAX_VOLTAGE, 4)
        self._validate_power(laser_power)

        self.pulsePal.isBiphasic[channel] = isBiphasic
        self.pulsePal.phase1Voltage[channel] = phase1Voltage
        self.pulsePal.restingVoltage[channel] = restingVoltage
        self.pulsePal.phase1Duration[channel] = round(float(phase1Duration), 3)

        ipi = 1 / float(pulse_frequency)
        self.pulsePal.interPulseInterval[channel] = round(ipi - phase1Duration, 3)
        self.pulsePal.pulseTrainDuration[channel] = float(pulseTrainDuration)
        self.pulsePal.pulseTrainDelay[channel] = round(float(pulseTrainDelay), 3)

    def set_power(self, laser_power: float, sync: bool = True):
        """Update laser power between trials/blocks without changing timing params.

        Maps laser_power (0.0–1.0) → phase1Voltage (0–5V) on the Doric LDFL5
        combined analog/TTL input. Call before triggering a new trial.

        Args:
            laser_power: Fractional power, 0.0 (off) to 1.0 (full).
            sync: If True, immediately sync to PulsePal hardware. Set False
                  if batching multiple parameter changes before a single sync.
        """
        self._validate_power(laser_power)
        self.in_dict["laser_power"] = laser_power
        phase1Voltage = round(float(laser_power) * DORIC_MAX_VOLTAGE, 4)

        for channel in self.in_dict["channels_stimulation"]:
            self.pulsePal.phase1Voltage[int(channel)] = phase1Voltage
            logging.info(
                f"PulsePal: Ch{channel} power set to {laser_power:.2f} "
                f"({phase1Voltage:.3f}V on Doric LDFL5 input)"
            )

        if sync:
            self.pulsePal.syncAllParams()

    def set_pulse_params(
            self,
            pulse_duration: float = None,
            pulse_frequency: float = None,
            pulse_train_duration: float = None,
            laser_power: float = None,
            sync: bool = True,
    ):
        """Update any combination of timing + power params between trials.

        Only updates params that are explicitly passed (not None).
        Useful for factorial optotagging protocols.
        """
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
                laser_power=float(self.in_dict["laser_power"]),
            )

        if sync:
            self.pulsePal.syncAllParams()

    def connect(self):
        self.pulsePal.connect(self.port)
        self.off()

        for channel in self.in_dict["channels_stimulation"]:
            self.pulsePal.setContinuousLoop(
                channel, 1 if self.in_dict["continuous"] else 0
            )

        self.pulsePal.syncAllParams()
        self.off()

        for channel in self.in_dict["trigger_channels_for_stimulation"]:
            if 0 < channel < 3:
                link_cmd = f"self.pulsePal.linkTriggerChannel{int(channel)} = {self.channels_stimulation[0]}"
                logging.info(f"PulsePal: Linking trigger channels: {link_cmd}.")
                exec(link_cmd)
                if (
                        "trigger_mode" in self.in_dict
                        and self.in_dict["trigger_mode"] in allowed_trigger_modes
                ):
                    self.pulsePal.triggerMode[channel] = allowed_trigger_modes[
                        self.in_dict["trigger_mode"]
                    ]

    def on(self):
        if not self.emergency_off_bool:
            self.pulsePal.triggerOutputChannels(*self.channels_stimulation[1:])
            self.channels_currently_active = self.channels_stimulation
            self.time_of_last_activation = time.time()
        else:
            raise NotImplementedError("Module has been turned off with emergency switch.")

    def off(self):
        if self.pulsePal is not None:
            self.pulsePal.abortPulseTrains()
            self.channels_currently_active = self.channels_inactive

    def _check_channels_active_reset(self):
        if abs(self.time_of_last_activation - time.time()) >= self.in_dict["reset_stimulation_after_sec"]:
            self.channels_currently_active = self.channels_inactive

    def trigger_clock(self):
        self._check_channels_active_reset()
        channels_to_switch = self.channels_clock_trigger[1:] + self.channels_currently_active[1:]
        self.pulsePal.triggerOutputChannels(*channels_to_switch)
        time.sleep(0.005)
        self.pulsePal.abortPulseTrains()

    def disconnect(self):
        if self.pulsePal is not None:
            self.pulsePal.abortPulseTrains()
            self.pulsePal.disconnect()
            self.pulsePal = []
        else:
            self.pulsePal = []

    def emergency_off(self):
        self.off()
        self.emergency_off_bool = True

    def is_open(self):
        try:
            return self.pulsePal.serialObject.serial_is_open
        except BaseException:
            logging.debug("Cannot check if PulsePal is connected.")
            return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.off()
        self.pulsePal.disconnect()
        logging.info("PulsePal: disconnected.")

    def __del__(self):
        self.off()
        self.pulsePal.disconnect()
        logging.info("PulsePal: disconnected.")

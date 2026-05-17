"""PulsePal stimulation wrapper using pypulsepal."""

import logging
import time

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
    }

    test = 0
    channels_currently_active = []
    emergency_off_bool = False

    def __init__(self, port=None, in_dict: dict = None, test: bool = False):
        self.test = test
        self.port = port
        for k, v in (in_dict or {}).items():
            self.in_dict[k] = v

        # Build PulsePal but don't connect yet — connect() called explicitly
        self.pulsePal = None

        for channel in self.in_dict["channels_stimulation"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                pulse_frequency=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
            )
            self.channels_stimulation[int(channel)] = 1

        for channel in self.in_dict["channel_trigger_clock"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=0.005,
                pulse_frequency=1,
                pulseTrainDuration=0.005,
                pulseTrainDelay=0,
            )
            self.channels_clock_trigger[int(channel)] = 1

    # -------------------------------------------------------------------------
    # Channel parameter storage (populated before connect; uploaded on connect)

    _channel_params: dict = None  # keyed by channel index

    def _ensure_params(self):
        if self._channel_params is None:
            self._channel_params = {}

    def _set_channel_params(
        self,
        channel=0,
        isBiphasic=0,
        phase1Voltage=5,
        restingVoltage=0,
        phase1Duration=0.005,
        pulse_frequency=0.05,
        pulseTrainDuration=3000.0,
        pulseTrainDelay=0.0,
    ):
        self._ensure_params()
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

    def connect(self):
        self.pulsePal = _PulsePal(serial_port=self.port)

        # Upload channel parameters
        self._ensure_params()
        for channel, params in self._channel_params.items():
            for param_name, value in params.items():
                self.pulsePal.program_one_param(
                    channel=channel, param_name=param_name, param_value=value
                )

        self.off()

        # Set continuous loop mode
        for channel in self.in_dict["channels_stimulation"]:
            self.pulsePal.set_continuous(
                channel=channel,
                state=1 if self.in_dict.get("continuous") else 0,
            )

        # Trigger channel links and modes
        for trigger_ch in self.in_dict["trigger_channels_for_stimulation"]:
            if 0 < trigger_ch < 3:
                # Link this trigger channel to stimulation output channels
                link_param = f"linkTriggerChannel{int(trigger_ch)}"
                for out_ch, active in enumerate(self.channels_stimulation[1:], start=1):
                    if active:
                        try:
                            self.pulsePal.program_one_param(
                                channel=trigger_ch - 1,
                                param_name=link_param,
                                param_value=out_ch,
                            )
                        except Exception as exc:
                            logging.warning(
                                f"PulsePal: could not set {link_param} for ch {out_ch}: {exc}"
                            )
                if (
                    "trigger_mode" in self.in_dict
                    and self.in_dict["trigger_mode"] in allowed_trigger_modes
                ):
                    self.pulsePal.program_trigger_channel(
                        trigger_channel=trigger_ch - 1,
                        trigger_mode=self.in_dict["trigger_mode"],
                    )

        logging.info(f"PulsePal: connected on {self.port}")

    def on(self):
        if not self.emergency_off_bool:
            ch = self.channels_stimulation[1:]
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

    def trigger_clock(self):
        self._check_channels_active_reset()
        ch = self.channels_clock_trigger[1:] + self.channels_currently_active[1:]
        self.pulsePal.trigger_selected_channels(
            channel_1=bool(ch[0]) if len(ch) > 0 else False,
            channel_2=bool(ch[1]) if len(ch) > 1 else False,
            channel_3=bool(ch[2]) if len(ch) > 2 else False,
            channel_4=bool(ch[3]) if len(ch) > 3 else False,
        )
        time.sleep(0.005)
        self.pulsePal.stop_all_outputs()

    def disconnect(self):
        if self.pulsePal is not None:
            try:
                self.pulsePal.stop_all_outputs()
                self.pulsePal.save_settings()
            except Exception:
                pass
            self.pulsePal = None
        logging.info("PulsePal: disconnected.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    def emergency_off(self):
        self.off()
        self.emergency_off_bool = True

    def is_open(self) -> bool:
        try:
            return self.pulsePal._arcom.serial_object.is_open
        except Exception:
            logging.debug("Cannot check if PulsePal is connected.")
            return False

"""Code written by Lars B. Rollik 2021."""
import time

from numpy import zeros

from pybpod_tools.external.PulsePal3 import PulsePalObject  # Import PulsePalObject
from pybpod_tools.misc import unpack_input_dict


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
        "trigger_channels_for_stimulation": [
            1
        ],  # values: 1,2 -- no python index offset here as is used for eval
        "channels_stimulation": [3],  # values: 0,1,2,3
        "channel_trigger_clock": [4],  # values: 0,1,2,3
        "reset_stimulation_after_sec": 0.005,
        # TODO: this option will be useful in paradigms that are not pseudo-pulse-gated
        #  (as rtpp: stim gets overwrite every time a new frame is evaluated by the tracking),
        #  e.g. when only one stim bout of a specific length should occur upon arrival in an ROI / other condition
    }

    test = 0  # for debugging
    channels_currently_active = []
    emergency_off_bool = False

    def __init__(self, port, in_dict={}, test=0):
        """Wrapper class for PulsePalObject
        :param port:
        :param in_dict:
        :param test:
        """
        # debug
        self.test = test

        # Connect to PulsePal on port COM3 (open port, handshake and receive firmware version)
        self.pulsePal = PulsePalObject()
        self.port = port

        if in_dict:
            self.in_dict = unpack_input_dict(self.in_dict, in_dict)

        # STIMULATION parameters
        for channel in self.in_dict["channels_stimulation"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=round(float(self.in_dict["pulse_duration"]), 3),
                interPulseInterval=round(float(self.in_dict["pulse_frequency"]), 3),
                pulseTrainDuration=float(self.in_dict["pulse_train_duration"]),
                pulseTrainDelay=round(float(self.in_dict["pulse_train_delay"]), 3),
            )

            self.channels_stimulation[int(channel)] = 1

        # TRIGGER FOR CLOCK (e.g. for ephys synch)
        for channel in self.in_dict["channel_trigger_clock"]:
            self._set_channel_params(
                channel=int(channel),
                phase1Duration=0.005,
                interPulseInterval=1,
                pulseTrainDuration=0.005,
                pulseTrainDelay=0,
            )

            self.channels_clock_trigger[int(channel)] = 1

        # SET LINK: TRIGGER -> STIMULATION (no equivalent for clock trigger as is determined by software)
        # for channel in self.in_dict["trigger_channels_for_stimulation"]:
        #     exec(
        #         "self.pulsePal.linkTriggerChannel"
        #         + str(int(channel))
        #         + " = self.channels_stimulation"
        #     )

    def _set_channel_params(
        self,
        channel=0,
        isBiphasic=0,
        phase1Voltage=5,
        restingVoltage=0,
        phase1Duration=0.005,
        interPulseInterval=0.05,
        pulseTrainDuration=3000.0,
        pulseTrainDelay=0.0,
    ):
        # isBiphasic = false
        self.pulsePal.isBiphasic[channel] = isBiphasic
        # phase1Voltage: 5V TTL pulses
        self.pulsePal.phase1Voltage[channel] = phase1Voltage
        # set channel #'s resting voltage (between pulses) to zero
        self.pulsePal.restingVoltage[channel] = restingVoltage

        # phase1Duration: # pulse width of 5ms
        self.pulsePal.phase1Duration[channel] = round(float(phase1Duration), 3)
        # inter-pulse interval = 0.05s ~ 20 Hz
        self.pulsePal.interPulseInterval[channel] = round(
            1 / float(interPulseInterval), 3
        )
        # total duration of pulses = 3000 sec
        self.pulsePal.pulseTrainDuration[channel] = float(pulseTrainDuration)
        # delay until pulse train starts
        self.pulsePal.pulseTrainDelay[channel] = round(float(pulseTrainDelay), 3)

    def connect(self):
        self.pulsePal.connect(self.port)

        self.pulsePal.setContinuousLoop(
            1, 1
        )  # (channel, mode): channel 1 to continuous / param=0 for non-continuous

        self.pulsePal.syncAllParams()
        self.pulsePal.abortPulseTrains()

    def on(self):
        if not self.emergency_off_bool:
            self.pulsePal.triggerOutputChannels(*self.channels_stimulation[1:])
            self.channels_currently_active = self.channels_stimulation
            self.time_of_last_activation = time.time()

    def off(self):
        self.pulsePal.abortPulseTrains()
        self.channels_currently_active = self.channels_inactive

    def _check_channels_active_reset(self):
        if (
            abs(self.time_of_last_activation - time.time())
            >= self.in_dict["reset_stimulation_after_sec"]
        ):
            self.channels_currently_active = self.channels_inactive

    def trigger_clock(self):
        self._check_channels_active_reset()
        # add active channel(s), so that clock trigger does not interrupt other channels
        channels_to_switch = (
            self.channels_clock_trigger[1:] + self.channels_currently_active[1:]
        )
        self.pulsePal.triggerOutputChannels(*channels_to_switch)
        time.sleep(0.005)
        self.pulsePal.abortPulseTrains()

    def disconnect(self):
        if self.pulsePal:
            self.pulsePal.abortPulseTrains()
            self.pulsePal.disconnect()
            self.pulsePal = []
        else:
            self.pulsePal = []

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.off()
        self.pulsePal.disconnect()

    def emergency_off(self):
        self.off()
        self.emergency_off_bool = True

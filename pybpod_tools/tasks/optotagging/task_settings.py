TTL_IDENTIFIER_SEQUENCE = "LLLLL"  # FIXME

PORT = "/dev/ttyACM1"
TRIGGER_CHANNELS_FOR_STIMULATION = [1]
STIMULATION_CHANNELS = [1]

N_MAX_TRIALS = 100
TRIGGER_ITI = 1  # seconds


class Presets:
    class Inhibition:
        params = {
            "pulse_duration": 1000,
            "pulse_frequency": 1,
            "pulse_train_duration": 1000,
            "pulse_train_delay": 0,
            "trigger_channels_for_stimulation": TRIGGER_CHANNELS_FOR_STIMULATION,  # values: 1,2 -- no python index offset here as is used for eval
            "channels_stimulation": STIMULATION_CHANNELS,  # values: 0,1,2,3
            "channel_trigger_clock": [4],  # values: 0,1,2,3
            "reset_stimulation_after_sec": 0.005,
        }

    class Excitation:
        params = {
            "pulse_duration": 0.005,
            "pulse_frequency": 20,
            "pulse_train_duration": 1,
            "pulse_train_delay": 0,
            "trigger_channels_for_stimulation": TRIGGER_CHANNELS_FOR_STIMULATION,  # values: 1,2 -- no python index offset here as is used for eval
            "trigger_mode": "gated",  # normal, toggle, pulse gate
            "channels_stimulation": STIMULATION_CHANNELS,  # values: 0,1,2,3
            "channel_trigger_clock": [4],  # values: 0,1,2,3
            "reset_stimulation_after_sec": 0.005,
            "continuous": False,
        }


selected_preset = Presets.Excitation.params  # TODO: SELECT preset here

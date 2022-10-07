import logging

import numpy as np
import sounddevice as sd


sample_rate_dict = {
    "sysdefault": 44100,
    "XONAR SOUND CARD": 192000,
}


def get_sample_rate(target_device_name=None):
    for k in sample_rate_dict.keys():
        if k in str(target_device_name):
            return sample_rate_dict[k]

    return None


def find_sound_device(target_device=None, return_first=True):
    devices = sd.query_devices()

    found_device = [
        (i, d) for i, d in enumerate(devices) if target_device in d["name"]
    ]
    if len(found_device) > 0 and return_first:
        found_device = found_device[0]
    return found_device


class StereoSound(object):
    _sounds = {}

    default_sound_device = "XONAR SOUND CARD"
    default_ttl_channel = 1  # choices: 0 or 1 -> idx of position on
    default_ttl_duration = 0.001  # 1 ms
    default_sound_channels = 2  # stereo
    default_sound_latency = "low"

    sound_device = None
    sample_rate = None
    ttl_channel = None
    ttl_duration = None

    sound_stop_code = 99

    def __init__(
        self,
        sound_device: str = None,
        sample_rate: int = None,
        ttl_channel: int = 1,
        ttl_duration: float = 0.001,
        allow_sys_default_device=True,
        **kwargs,
    ):
        """ """
        super(StereoSound, self).__init__()
        # Check args
        found_input_device = (
            find_sound_device(target_device=sound_device)
            if sound_device is not None
            else None
        )
        self.sound_device = found_input_device or find_sound_device(
            target_device=self.default_sound_device
        )

        if not self.sound_device:
            if not allow_sys_default_device:
                raise ValueError(
                    f"No sound device found for input '{sound_device}' "
                    f"or default '{self.default_sound_device}'"
                )
            else:
                self.sound_device = "sysdefault"

        self.sample_rate = sample_rate or get_sample_rate(
            target_device_name=self.sound_device[1]["name"]
            if not isinstance(self.sound_device, str)
            else self.sound_device
        )
        if self.sample_rate is None:
            raise ValueError(
                f"Could not find sample rate for device '{self.sound_device}'. "
                f"Change device or provide sample rate in input."
            )

        self.ttl_channel = ttl_channel or self.default_ttl_channel
        if self.ttl_channel != 0 and self.ttl_channel != 1:
            raise ValueError(
                f"'ttl_channel' has to be 0 or 1 for stereo output, but '{self.ttl_channel}' given"
            )

        self.ttl_duration = ttl_duration or self.default_ttl_duration

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @property
    def sounds(self):
        return self._sounds

    @sounds.setter
    def sounds(self, new_sounds: dict):
        self._sounds = new_sounds

    def setup_sound_device(self):
        """Set required overwrites for sound device."""
        sd.default.device = self.sound_device
        sd.default.latency = self.default_sound_latency
        sd.default.channels = self.default_sound_channels
        sd.default.samplerate = self.sample_rate

    def _make_sound(
        self,
        frequency=None,
        duration=None,
        amplitude=None,
        fade_duration=0.01,
    ):
        """Original code similar to
        https://github.com/int-brain-lab/iblrig/blob/0ee17a14633f0dc7b87f268f433a027e73fd6d57/iblrig/sound.py#L47
        Refactored as was always only for stereo output with mono sound + optional TTL.
        """
        tvec = np.linspace(0, duration, int(duration * self.sample_rate))
        tone = amplitude * np.sin(2 * np.pi * frequency * tvec)  # tone vec

        len_fade = int(fade_duration * self.sample_rate)
        fade_io = np.hanning(len_fade * 2)
        fadein = fade_io[:len_fade]
        fadeout = fade_io[len_fade:]
        win = np.ones(len(tvec))
        win[:len_fade] = fadein
        win[-len_fade:] = fadeout

        tone = tone * win
        ttl = np.ones(len(tone)) * 0.99
        one_ms = np.array(
            (self.sample_rate / 1000) * self.ttl_duration
        ).astype(int)
        ttl[one_ms:] = 0
        null = np.zeros(len(tone))

        if frequency == -1:
            tone = amplitude * np.random.rand(tone.size)

        if self.ttl_channel is not None:
            if self.ttl_channel == 0:
                sound = np.array([tone, null]).T
            elif self.ttl_channel == 1:
                sound = np.array([null, tone]).T
            else:
                raise ValueError(
                    f"'ttl_channel' has to be 0 or 1 for stereo output, but '{self.ttl_channel}' given"
                )
        else:
            return np.array(tone)

        return sound

    def register_new_sound(
        self,
        frequency=None,
        duration=None,
        amplitude=None,
        fade_duration=0.01,
        play_blocking=True,
        **kwargs,
    ):
        """ """
        new_sound_dict = kwargs
        new_sound_dict["play_blocking"] = play_blocking
        new_sound_dict["sound"] = self._make_sound(
            frequency=frequency,
            duration=duration,
            amplitude=amplitude,
            fade_duration=fade_duration,
        )

        new_sound_key = len(self._sounds)
        self._sounds[new_sound_key] = new_sound_dict
        return new_sound_key

    def execute_sound_handler(self, sound_code=None, raise_errors=False):
        if sound_code in self.sounds.keys():
            logging.debug(f"Playing sound # {sound_code}.")
            sd.play(
                self.sounds[sound_code]["sound"],
                self.sample_rate,
                blocking=self.sounds[sound_code]["play_blocking"],
            )
        elif sound_code == self.sound_stop_code:
            logging.debug("Stopped current sound.")
            sd.stop()
        else:
            msg = f"No such sound index: {sound_code}"
            if raise_errors:
                raise ValueError(msg)
            else:
                logging.info(msg)


if __name__ == "__main__":
    print(" ")

import logging
from typing import Optional

import numpy as np
import sounddevice as sd

sample_rate_dict = {
    "sysdefault": 44100,
    "default": 44100,
    "pipewire": 44100,
    "HDA Intel PCH": 44100,
    "XONAR SOUND CARD": 192000,
    "XONAR AE": 192000,
}


def get_sample_rate(target_device_name=None):
    for k in sample_rate_dict.keys():
        if k in str(target_device_name):
            return sample_rate_dict[k]

    return None


def find_sound_device(target_device=None, return_first=True):
    devices = sd.query_devices()

    found_device = [(i, d) for i, d in enumerate(devices) if target_device in d["name"]]
    if len(found_device) > 0 and return_first:
        found_device = found_device[0]
    return found_device


class StereoSound(object):
    default_sound_device = "XONAR SOUND CARD"
    default_ttl_channel = 1  # choices: 0 or 1 -> idx of position on
    default_ttl_duration = 0.001  # 1 ms
    default_sound_channels = 2  # stereo
    default_sound_latency = "low"

    sound_stop_code = 99

    def __init__(
        self,
        sound_device: Optional[str] = None,
        sample_rate: Optional[int] = None,
        ttl_channel: int = 1,
        ttl_duration: float = 0.001,
        allow_sys_default_device=True,
        **kwargs,
    ):
        super(StereoSound, self).__init__()

        # Instance-level sounds dict (not class-level — avoid cross-instance sharing)
        self._sounds: dict = {}

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
                logging.warning(
                    f"Sound device '{sound_device or self.default_sound_device}' not found "
                    f"— falling back to system default output."
                )
                self.sound_device = "sysdefault"

        _dev_dict = (
            self.sound_device[1] if not isinstance(self.sound_device, str) else {}
        )
        # Extract int index for explicit device passing to sd.play(); keep full tuple
        # on self.sound_device for backward compatibility with callers that read it.
        if isinstance(self.sound_device, (list, tuple)):
            self._device_id = self.sound_device[0]
        else:
            self._device_id = self.sound_device  # string fallback ("sysdefault")

        _sr: int | None = (
            sample_rate
            or get_sample_rate(
                target_device_name=_dev_dict.get("name", self.sound_device)
            )
            or int(_dev_dict.get("default_samplerate", 0))
            or None
        )
        if _sr is None:
            raise ValueError(
                f"Could not find sample rate for device '{self.sound_device}'. "
                f"Change device or provide sample rate in input."
            )
        self.sample_rate: int = _sr

        self.ttl_channel = ttl_channel or self.default_ttl_channel
        if self.ttl_channel != 0 and self.ttl_channel != 1:
            raise ValueError(
                f"'ttl_channel' has to be 0 or 1 for stereo output, but '{self.ttl_channel}' given"
            )

        self.ttl_duration = ttl_duration or self.default_ttl_duration

        dev_name = _dev_dict.get("name", self.sound_device)
        logging.info(
            f"StereoSound: device={dev_name!r} id={self._device_id} sr={self.sample_rate}"
        )

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
        """Set sounddevice global defaults for this device."""
        sd.default.device = self._device_id
        sd.default.latency = self.default_sound_latency
        sd.default.channels = self.default_sound_channels
        sd.default.samplerate = self.sample_rate

    def _make_bup(self, amplitude: float) -> np.ndarray:
        """Single 5 ms broadband bup matching the MATLAB singlebup defaults.

        Harmonics at 2k, 4k, 8k, 16k Hz summed equally, normalised, then
        amplitude-scaled.  2 ms cos²-ramp applied to onset and offset.
        """
        bup_dur = int(0.005 * self.sample_rate)
        t = np.arange(bup_dur) / self.sample_rate
        bup = sum(np.sin(2 * np.pi * f * t) for f in (2000, 4000, 8000, 16000))
        peak = np.max(np.abs(bup))
        if peak > 0:
            bup /= peak
        ramp_n = int(0.002 * self.sample_rate)
        ramp = np.cos(np.linspace(np.pi / 2, 0, ramp_n)) ** 2
        bup[:ramp_n] *= ramp[::-1]
        bup[-ramp_n:] *= ramp
        return amplitude * bup

    def _make_bup_train(
        self,
        bup_rate: float = 5.0,
        duration: float = 1.5,
        amplitude: float = 0.05,
    ) -> np.ndarray:
        """Train of bups matching the MATLAB MakeBupperSwoop reward sound.

        Default parameters replicate: MakeBupperSwoop(sr, 0, 5, 5, 750, 750, 0, 0.1)
        — 5 Hz bup rate, 1.5 s total, broadband clicks.
        """
        n_samples = int(duration * self.sample_rate)
        mono = np.zeros(n_samples)
        bup = self._make_bup(amplitude)
        interval = int(self.sample_rate / bup_rate)
        for start in range(0, n_samples, interval):
            end = min(start + len(bup), n_samples)
            mono[start:end] += bup[: end - start]
        return mono

    def _make_sound(
        self,
        frequency=None,
        duration=None,
        amplitude=None,
        fade_duration=0.01,
        bup_rate: float = 5.0,
    ):
        """Build a stereo sound array.

        frequency=-2 → bup train (MATLAB MakeBupperSwoop style, broadband clicks).
        frequency=-1 → white noise.
        frequency>0  → pure sine tone.
        """
        if frequency == -2:
            mono = self._make_bup_train(
                bup_rate=bup_rate, duration=duration, amplitude=amplitude
            )
        else:
            tvec = np.linspace(0, duration, int(duration * self.sample_rate))
            if frequency == -1:
                mono = amplitude * np.random.randn(len(tvec))
            else:
                mono = amplitude * np.sin(2 * np.pi * frequency * tvec)

            len_fade = int(fade_duration * self.sample_rate)
            fade_io = np.hanning(len_fade * 2)
            win = np.ones(len(tvec))
            win[:len_fade] = fade_io[:len_fade]
            win[-len_fade:] = fade_io[len_fade:]
            mono = mono * win

        null = np.zeros(len(mono))
        if self.ttl_channel == 0:
            return np.array([mono, null]).T
        elif self.ttl_channel == 1:
            return np.array([null, mono]).T
        else:
            raise ValueError(
                f"'ttl_channel' has to be 0 or 1 for stereo output, but '{self.ttl_channel}' given"
            )

    def register_new_sound(
        self,
        frequency=None,
        duration=None,
        amplitude=None,
        fade_duration=0.01,
        play_blocking=True,
        bup_rate: float = 5.0,
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
            bup_rate=bup_rate,
        )

        # 1-indexed: Bpod SoftCode 0 is not a valid user softcode
        new_sound_key = len(self._sounds) + 1
        self._sounds[new_sound_key] = new_sound_dict
        return new_sound_key

    def execute_sound_handler(self, sound_code=None, raise_errors=False):
        if sound_code in self.sounds.keys():
            logging.debug(f"Playing sound # {sound_code}.")
            sd.play(
                self.sounds[sound_code]["sound"],
                self.sample_rate,
                device=self._device_id,
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
                logging.debug(msg)


if __name__ == "__main__":
    print(" ")

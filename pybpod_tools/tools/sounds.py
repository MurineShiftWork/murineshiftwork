import logging
import sys

import numpy as np
import sounddevice as sd


def _get_samplerate(chosen_device=None):
    chosen_device = chosen_device.lower()
    if "xonar" in chosen_device:
        return 192000
    elif "sysdefault" in chosen_device:
        return 44100
    else:
        logging.error(f"Sound device not recognised: {chosen_device}")


class Sounds(object):
    ttl = "L+TTL"
    ttl_duration_msec = 1

    default_device = "XONAR SOUND CARD"
    default_latency = "low"
    default_channels = 2
    default_samplerate = 192000
    default_sound_blocking = True
    default_sound_fade = 0.01

    sound_go_array = None
    sound_stop_array = None
    sound_test_array = None

    sound_go_softcode = 1
    sound_stop_softcode = 2
    sound_test_softcode = 3
    sound_end_softcode = 99

    sound_go_params = {
        "frequency": 5000,
        "tone_duration": 0.1,
        "amplitude": 0.2,
    }
    sound_stop_params = {
        "frequency": -1,  # -1=noise
        "tone_duration": 0.1,
        "amplitude": 0.2,
    }
    sound_test_params = {
        "frequency": 5000,
        "tone_duration": 0.1,
        "amplitude": 0.01,
    }

    def __init__(self, sound_device="XONAR SOUND CARD", ttl="L+TTL"):
        super(Sounds, self).__init__()

        self.ttl = ttl

        self.setup_sound_output(
            sound_device=sound_device if sound_device else self.default_device
        )

        self.sound_go_array = self.make_sound(
            **self.sound_go_params,
            sample_rate=self.default_samplerate,
            chans=ttl,
            fade_duration=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )
        self.sound_stop_array = self.make_sound(
            **self.sound_stop_params,
            sample_rate=self.default_samplerate,
            chans=ttl,
            fade_duration=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )
        self.sound_test_array = self.make_sound(
            **self.sound_test_params,
            sample_rate=self.default_samplerate,
            chans=ttl,
            fade_duration=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )

    def soft_code_handler_function(self, softcode=None):
        logging.debug("Entering softcode handler.")
        if softcode == self.sound_go_softcode:
            logging.debug("playing sound: go")
            sd.play(
                self.sound_go_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif softcode == self.sound_stop_softcode:
            logging.debug("playing sound: stop")
            sd.play(
                self.sound_stop_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif softcode == self.sound_test_softcode:
            logging.debug("playing sound: test")
            sd.play(
                self.sound_test_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif softcode == self.sound_end_softcode:
            logging.debug("stopped sound")
            sd.stop()
        else:
            pass
        logging.debug("Exiting softcode handler.")

    def make_sound(
        self,
        sample_rate=44100,
        frequency=5000,
        tone_duration=0.1,
        amplitude=1,
        fade_duration=0.01,
        chans="L+TTL",
        ttl_duration_msec=1,
    ):
        """Make sound function taken from IBLRIG package.

        Build sounds and save bin file for upload to soundcard or play via
        sounddevice lib.
        :param sample_rate: sample rate of the soundcard use 96000 for Bpod,
                        defaults to 44100 for soundcard
        :type sample_rate: int, optional
        :param frequency: (Hz) of the tone, if -1 will create uniform random white
                        noise, defaults to 10000
        :type frequency: int, optional
        :param tone_duration: (s) of sound, defaults to 0.1
        :type tone_duration: float, optional
        :param amplitude: E[0, 1] of the sound 1=max 0=min, defaults to 1
        :type amplitude: intor float, optional
        :param fade_duration: (s) time of fading window rise and decay, defaults to 0.01
        :type fade_duration: float, optional
        :param chans: ['mono', 'L', 'R', 'stereo', 'L+TTL', 'TTL+R'] number of
                       sound channels and type of output, defaults to 'L+TTL'
        :type chans: str, optional
        :return: stereo sound from mono definitions
        :rtype: np.ndarray with shape (Nsamples, 2)
        """
        tvec = np.linspace(0, tone_duration, int(tone_duration * sample_rate))
        tone = amplitude * np.sin(2 * np.pi * frequency * tvec)  # tone vec

        len_fade = int(fade_duration * sample_rate)
        fade_io = np.hanning(len_fade * 2)
        fadein = fade_io[:len_fade]
        fadeout = fade_io[len_fade:]
        win = np.ones(len(tvec))
        win[:len_fade] = fadein
        win[-len_fade:] = fadeout

        tone = tone * win
        ttl = np.ones(len(tone)) * 0.99
        one_ms = (
            round(sample_rate / 1000) * ttl_duration_msec
        )  # LBR: original value was *10 for 1ms, but 5ms seems more stable for detection on bpod
        ttl[one_ms:] = 0
        null = np.zeros(len(tone))

        if frequency == -1:
            tone = amplitude * np.random.rand(tone.size)

        if chans == "mono":
            sound = np.array(tone)
        elif chans == "L":
            sound = np.array([tone, null]).T
        elif chans == "R":
            sound = np.array([null, tone]).T
        elif chans == "stereo":
            sound = np.array([tone, tone]).T
        elif chans == "L+TTL":
            sound = np.array([tone, ttl]).T
        elif chans == "TTL+R":
            sound = np.array([ttl, tone]).T
        else:
            raise ValueError(f"Cannot interpret chans param: {chans}")

        return sound

    def setup_sound_output(self, sound_device=None):
        devices = sd.query_devices()

        chosen_device = [
            (i, d) for i, d in enumerate(devices) if sound_device in d["name"]
        ]
        if len(chosen_device) > 1:
            sd.default.device = chosen_device[0][0]
            chosen_device = chosen_device[0][1]["name"]
        elif len(chosen_device) < 1 and sys.platform == "linux":
            sd.default.device = "sysdefault"
            chosen_device = "sysdefault"
        else:
            raise OSError(f"Could not find device '{sound_device}'")

        sd.default.latency = self.default_latency
        sd.default.channels = self.default_channels

        self.default_samplerate = _get_samplerate(chosen_device=chosen_device)
        logging.info(f"Sound sample sample_rate set to {self.default_samplerate}")
        sd.default.samplerate = self.default_samplerate

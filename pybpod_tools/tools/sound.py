import sys

import numpy as np
import sounddevice as sd


class Sound(object):
    ttl = None
    ttl_duration_msec = 1

    default_device = "sysdefault"
    default_latency = "low"
    default_channels = 2
    default_samplerate = 44100
    default_sound_blocking = True
    default_sound_fade = 0.01

    sound_go_array = None
    sound_stop_array = None
    sound_test_array = None

    sound_go_params = {
        "frequency": 5000,
        "duration": 0.1,
        "amplitude": 0.05,
    }
    sound_stop_params = {
        "frequency": -1,  # -1=noise
        "duration": 0.1,
        "amplitude": 0.05,
    }
    sound_test_params = {
        "frequency": 5000,
        "duration": 0.05,
        "amplitude": 0.05,
    }

    def __init__(self, sound_device="XONAR SOUND CARD", ttl="L+TTL"):
        super(Sound, self).__init__()

        self.ttl = ttl

        self.setup_sound_output(
            sound_device=sound_device if sound_device else self.default_device
        )

        self.sound_go_array = self.make_sound(
            **self.sound_go_params,
            rate=self.default_samplerate,
            chans=ttl,
            fade=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )
        self.sound_stop_array = self.make_sound(
            **self.sound_stop_params,
            rate=self.default_samplerate,
            chans=ttl,
            fade=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )
        self.sound_test_array = self.make_sound(
            **self.sound_test_params,
            rate=self.default_samplerate,
            chans=ttl,
            fade=self.default_sound_fade,
            ttl_duration_msec=self.ttl_duration_msec,
        )

    def soft_code_handler_function(self, key=None):
        print("Entering softcode handler.")
        if key == 1:
            print("playing sound: go")
            sd.play(
                self.sound_go_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif key == 2:
            print("playing sound: stop")
            sd.play(
                self.sound_stop_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif key == 3:
            print("playing sound: test")
            sd.play(
                self.sound_test_array,
                self.default_samplerate,
                blocking=self.default_sound_blocking,
            )
        elif key == 99:
            print("stopped sound")
            sd.stop()
        else:
            pass
        print("Exiting softcode handler.")

    def make_sound(
        self,
        rate=44100,
        frequency=5000,
        duration=0.1,
        amplitude=1,
        fade=0.01,
        chans="L+TTL",
        ttl_duration_msec=1,
    ):
        """Make sound function taken from IBLRIG package.

        Build sounds and save bin file for upload to soundcard or play via
        sounddevice lib.
        :param rate: sample rate of the soundcard use 96000 for Bpod,
                        defaults to 44100 for soundcard
        :type rate: int, optional
        :param frequency: (Hz) of the tone, if -1 will create uniform random white
                        noise, defaults to 10000
        :type frequency: int, optional
        :param duration: (s) of sound, defaults to 0.1
        :type duration: float, optional
        :param amplitude: E[0, 1] of the sound 1=max 0=min, defaults to 1
        :type amplitude: intor float, optional
        :param fade: (s) time of fading window rise and decay, defaults to 0.01
        :type fade: float, optional
        :param chans: ['mono', 'L', 'R', 'stereo', 'L+TTL', 'TTL+R'] number of
                       sound channels and type of output, defaults to 'L+TTL'
        :type chans: str, optional
        :return: stereo sound from mono definitions
        :rtype: np.ndarray with shape (Nsamples, 2)
        """
        sample_rate = rate  # Sound card dependent,
        tone_duration = duration  # sec
        fade_duration = fade  # sec

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
            round(sample_rate / 1000) * 10 * ttl_duration_msec
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
        elif len(chosen_device) < 1 and sys.platform == "linux":
            sd.default.device = "sysdefault"
        else:
            raise OSError(f"Could not find device '{sound_device}'")

        sd.default.latency = self.default_latency
        sd.default.channels = self.default_channels
        sd.default.samplerate = self.default_samplerate

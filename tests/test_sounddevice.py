import time

import numpy as np
import sounddevice as sd
from scipy.signal import chirp

devices = sd.query_devices()

sd.default.device = [
    (i, d) for i, d in enumerate(devices) if "XONAR SOUND CARD" in d["name"]
][0][0]

sd.default.latency = "low"
sd.default.channels = 2
sd.default.samplerate = 44100

# if sys.platform == "linux"
output = "sysdefault"


def make_sound(
    rate=44100, frequency=5000, duration=0.1, amplitude=1, fade=0.01, chans="L+TTL"
):
    """
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
    :return: streo sound from mono definitions
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
    one_ms = round(sample_rate / 1000) * 10
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

    return sound


sound_1 = make_sound(rate=44100, duration=1, amplitude=0.5, frequency=-1, chans="TTL+R")
sd.play(sound_1, 44100, mapping=[1, 2])

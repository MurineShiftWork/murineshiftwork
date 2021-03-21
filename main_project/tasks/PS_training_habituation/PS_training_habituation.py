import logging

import numpy as np
import matplotlib.pyplot as plt
from pybpodapi.protocol import Bpod, StateMachine

MAX_TRIALS = 1500

# open bpod connection
bpod = Bpod()

# make objects for TaskControl, OnlinePlotting, ParamsSettings

# If camera=True, try to execute a camera protocol for RPi cameras with current session name

for tidx in np.arange(MAX_TRIALS):
    # make state machine
    sma = StateMachine(bpod=bpod)

    # TTL on/off states
    # Center wait for init
    # Side wait for entry
    # Outcome: correct->reward, wrong->finish, stop+punish-> air
    # Finish: wait for poke out

    # EXE state machine

    # update log
    # update fig
    # update task progress

    print(" ")

# close bpod

# If camera=True, try to clean up camera object

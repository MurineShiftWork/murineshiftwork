import logging
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from pybpod_tools.tools.sounds import Sounds

# TODO: move sound functions to module + create loop to go over many trials.
#  TTL delay should be <100ms, so 200ms trials should be fine to get correct estimate for sound delay

# TODO: ask for bnc channel to use for TTL out
# TODO: remove all delays to enable high frequency test for estimate of at least 100 pulses/sounds

sounds = Sounds()

bpod = Bpod()
bpod.softcode_handler_function = sounds.soft_code_handler_function
bnc_channel = Bpod.OutputChannels.BNC2

delay_measurements = []

for trial_index in np.arange(201):
    print(f"\ntrial {trial_index}")

    sma = StateMachine(bpod=bpod)

    sma.add_state(
        state_name="sound_and_bnc_on",
        state_timer=0.005,
        state_change_conditions={"Tup": "bnc_off"},
        output_actions=[("SoftCode", 3), (bnc_channel, 1)],
    )
    sma.add_state(
        state_name="bnc_off",
        state_timer=0.1,
        state_change_conditions={"Tup": "leave"},
        output_actions=[(bnc_channel, 0)],  # ("SoftCode", 99),
    )
    sma.add_state(
        state_name="leave",
        state_timer=0,
        state_change_conditions={"Tup": "exit"},
        output_actions=[("SoftCode", 99)],
    )

    # EXECUTE trial
    dt = time.time()
    bpod.send_state_machine(sma)  # Send state machine description to Bpod device

    if not bpod.run_state_machine(sma):
        print("nothing returned")

    print(f"Trial took {time.time()-dt}s")

    ev = bpod.session.current_trial.export()["Events timestamps"]
    delay = dict(ev).get("BNC1High", -1)
    if not delay == -1:
        delay_measurements.append({"trial": trial_index, "delay": delay[0]})
    else:
        raise ValueError(f"Did not receive TTL on trial {trial_index}")

    print(f"Trial {trial_index}:", delay)


delay_measurements_df = pd.DataFrame(delay_measurements)
delays = delay_measurements_df["delay"] * 1000  # convert to msec
print(
    f"Delay sound trigger to soundcard TTL is "
    f"MEAN={np.round(delays.mean(),3)}ms, "
    f"MEDIAN={np.round(delays.median(),3)}ms, "
    f"STD={np.round(delays.std(),3)}ms"
)

# Plot delays for inspection
plt.plot(delays, "k*--")
plt.title("Delays sound softcode to soundcard TTL received by Bpod.")
plt.ylabel("Delay [ms]")
plt.xlabel("Trial [#]")
plt.show()

bpod.close()

if __name__ == "__main__":
    print("main")

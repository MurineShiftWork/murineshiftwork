import logging
import time

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from pybpod_tools.tools.sound import Sound

# TODO: move sound functions to module + create loop to go over many trials. TTL delay should be <100ms, so 200ms trials should be fine to get correct estimate for sound delay

sounds = Sound()

bpod = Bpod()
bpod.softcode_handler_function = sounds.soft_code_handler_function()
bnc_channel = Bpod.OutputChannels.BNC2

for t in np.arange(50):
    print(f"\ntrial {t}")
    time.sleep(1)

    sma = StateMachine(bpod=bpod)

    sma.add_state(
        state_name="x",
        state_timer=0.005,
        state_change_conditions={"Tup": "next"},
        output_actions=[("SoftCode", 1), (bnc_channel, 1)],
    )
    sma.add_state(
        state_name="next",
        state_timer=2,
        state_change_conditions={"Tup": "last"},
        output_actions=[(bnc_channel, 0)],  # ("SoftCode", 99),
    )
    sma.add_state(
        state_name="last",
        state_timer=1,
        state_change_conditions={"Tup": "exit"},
        output_actions=[("SoftCode", 99)],
    )

    # EXECUTE trial
    bpod.send_state_machine(sma)  # Send state machine description to Bpod device

    if not bpod.run_state_machine(sma):
        print("nothing returned")

    print(f"trial {t}:", bpod.session.current_trial.export()["Events timestamps"])
    time.sleep(2)

bpod.close()

if __name__ == "__main__":
    print("main")

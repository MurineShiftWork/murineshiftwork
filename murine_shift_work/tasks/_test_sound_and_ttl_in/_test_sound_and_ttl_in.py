import logging
import time
from pathlib import Path

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from murine_shift_work.logic.calibration import save_sound_delay_data
from murine_shift_work.logic.paths import make_session_paths
from murine_shift_work.logic.sounds import Sounds


class TestSettings:
    bnc_channel = Bpod.OutputChannels.BNC1


test_settings = TestSettings()
sounds = Sounds()
session_paths = make_session_paths(protocol=Path(__file__).parent.name)
bpod = Bpod(
    workspace_path=session_paths["session_data_folder"],
    session_name=session_paths["session_basename"],
)
bpod.softcode_handler_function = sounds.soft_code_handler_function

delay_measurements = []

for trial_index in np.arange(201):
    logging.debug(f"\ntrial {trial_index}")

    sma = StateMachine(bpod=bpod)

    sma.add_state(
        state_name="sound_and_bnc_on",
        state_timer=0.005,
        state_change_conditions={"Tup": "bnc_off"},
        output_actions=[
            ("SoftCode", sounds.sound_test_softcode),
            (test_settings.bnc_channel, 1),
        ],
    )
    sma.add_state(
        state_name="bnc_off",
        state_timer=0.1,
        state_change_conditions={"Tup": "leave"},
        output_actions=[(test_settings.bnc_channel, 0)],  # ("SoftCode", 99),
    )
    sma.add_state(
        state_name="leave",
        state_timer=0,
        state_change_conditions={"Tup": "exit"},
        output_actions=[("SoftCode", sounds.sound_end_softcode)],
    )

    # EXECUTE trial
    dt = time.time()
    bpod.send_state_machine(sma)

    if not bpod.run_state_machine(sma):
        print("nothing returned")

    logging.debug(f"Trial took {time.time()-dt}s")

    ev = bpod.session.current_trial.export()["Events timestamps"]
    delay = dict(ev).get("BNC1High", -1)
    if not delay == -1:
        delay_measurements.append({"trial": trial_index, "delay": delay[0]})
    else:
        logging.error(f"Did not receive TTL on trial {trial_index}")

    logging.info(f"Trial {trial_index}: Delay of {delay}s")


save_sound_delay_data(measurements=delay_measurements)
bpod.close()

if __name__ == "__main__":
    print("main")

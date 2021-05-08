import logging

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from pybpod_tools.stimulation import Stimulation
from pybpod_tools.tasks.optotagging import task_settings
from pybpod_tools.tools.specific_state_machines import add_trial_onset_ttl
from pybpod_tools.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)


bpod = Bpod()
stimulation = Stimulation(
    port=task_settings.PORT,
    in_dict=task_settings.selected_preset,
)

for trial_index in np.arange(task_settings.N_MAX_TRIALS):
    print(f"Executing trial {trial_index}")

    if trial_index == 0:
        sma = make_protocol_identifier_ttl_sequence(
            bpod=bpod,
            sequence=task_settings.TTL_IDENTIFIER_SEQUENCE,
            output_chanel_pulse=Bpod.OutputChannels.BNC2,
        )
    else:
        sma = StateMachine(bpod=bpod)

        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=0.001,
            bnc_channel=[Bpod.OutputChannels.BNC1, Bpod.OutputChannels.BNC2],
            next_state="iti",
        )

        sma.add_state(
            state_name="iti",
            state_timer=task_settings.TRIGGER_ITI,
            state_change_conditions={Bpod.Events.Tup: "exit"},
            output_actions=[],
        )

    bpod.send_state_machine(sma)

    if not bpod.run_state_machine(sma):
        logging.warning(
            f"No data returned on trial #{trial_index}. Terminating protocol."
        )
        break

bpod.close()


if __name__ == "__main__":
    print("main")

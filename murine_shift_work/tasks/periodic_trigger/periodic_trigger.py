import logging
from pathlib import Path

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine

from murine_shift_work.logic.paths import make_session_paths
from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)

N_MAX_TRIALS = 1500
TTL_IDENTIFIER_SEQUENCE = None  # FIXME
TRIGGER_ITI = 5  # seconds

session_paths = make_session_paths(protocol=Path(__file__).parent.name)
bpod = Bpod(
    workspace_path=session_paths["session_data_folder"],
    session_name=session_paths["session_basename"],
)

for trial_index in np.arange(N_MAX_TRIALS):
    if trial_index == 0:
        sma = make_protocol_identifier_ttl_sequence(
            bpod=bpod,
            sequence=TTL_IDENTIFIER_SEQUENCE,
            output_chanel_pulse=Bpod.OutputChannels.BNC2,
        )
    else:
        sma = StateMachine(bpod=bpod)

        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=0.001,
            bnc_channel=Bpod.OutputChannels.BNC2,
            next_state="iti",
        )

        sma.add_state(
            state_name="iti",
            state_timer=TRIGGER_ITI,
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

import logging

import numpy as np
from pybpodapi.protocol import Bpod

from pybpod_tools.tasks.probabilistic_switching import task_settings
from pybpod_tools.tasks.probabilistic_switching.task_objects import TaskControl
from pybpod_tools.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)

bpod = Bpod()
task_control = TaskControl(bpod=bpod)
bpod.softcode_handler_function = task_control.softcode_handler

for trial_index in np.arange(task_settings.N_MAX_TRIALS):
    logging.info(f"Trial: {trial_index}")

    if trial_index == 0 and not task_settings.TESTING:
        sma = make_protocol_identifier_ttl_sequence(
            bpod=bpod,
            sequence=task_settings.TTL_IDENTIFIER_SEQUENCE,
            output_chanel_pulse=Bpod.OutputChannels.BNC2,
        )
    else:
        sma = task_control.draw_next_trial()

    bpod.send_state_machine(sma)

    if not bpod.run_state_machine(sma):
        logging.warning(
            f"No data returned on trial #{trial_index}. Terminating protocol."
        )
        break

    trial_data = bpod.session.current_trial.export()
    task_control.update(trial_index=trial_index, trial_data=trial_data)

task_control.save()
bpod.close()

if __name__ == "__main__":
    print("main")

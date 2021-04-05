import logging

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from pybpod_tools.tasks.probabilistic_switching import task_settings
from pybpod_tools.tasks.probabilistic_switching.task_objects import OnlinePlotting
from pybpod_tools.tasks.probabilistic_switching.task_objects import TaskControl
from pybpod_tools.tasks.probabilistic_switching.task_objects import TaskData
from pybpod_tools.tools.misc import get_session_file_basename
from pybpod_tools.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)

# TODO: write basic SMA for PS task, including block update rules fixed trials vs criterion
# TODO: write TTL sequence function for ephys synch
# TODO: write online plotting functions
# TODO: write analysis module to save data preprocessed

# Bpod startup
bpod = Bpod()

# Task objects
save_path_basename = get_session_file_basename(bpod)
task_control = TaskControl(bpod=bpod)
task_data = TaskData(save_path=save_path_basename)
online_plotting = OnlinePlotting(save_path=save_path_basename)

# Bpod event handlers
bpod.loop_handler = online_plotting.bpod_loop_handler
bpod.softcode_handler_function = task_control.softcode_handler

for trial_index in np.arange(task_settings.N_MAX_TRIALS):  # Main loop
    print("Trial: ", trial_index + 1)

    if trial_index == 0 and not task_settings.TESTING:
        sma = make_protocol_identifier_ttl_sequence(
            bpod=bpod,
            sequence=task_settings.TTL_IDENTIFIER_SEQUENCE,
            output_chanel_pulse=Bpod.OutputChannels.BNC2,
        )
    else:
        sma = task_control.draw_next_trial()
        pass
        # if not task_control.current_probabilities: make first block or if block_switch_criterion: make new block
        # draw trial from block structure
        # TODO: need multiple SMA for simple training tasks and for air puff, light, stop signal white noise

    # EXECUTE trial
    bpod.send_state_machine(sma)

    if not bpod.run_state_machine(sma):
        logging.info(f"No data returned on trial #{trial_index}. Terminating protocol.")

    task_data.append(bpod.session.current_trial.export())
    online_plotting.update(task_data=task_data)

    # TODO: control task: (a) next block?, (b) trial types?

task_data.save()
online_plotting.save()
bpod.close()  # Disconnect Bpod

if __name__ == "__main__":
    print("main")

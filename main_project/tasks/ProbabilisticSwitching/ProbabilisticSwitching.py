import logging

import numpy as np
import matplotlib.pyplot as plt
from pybpodapi.protocol import Bpod

from task_objects import TaskControl, TaskData
from .tools import softcode_handler

bpod = Bpod(serial_port=None)
task_control = TaskControl(bpod=bpod)
task_data = TaskData(save_path="test")  # fixme: get savepath from session path

for trial_index in np.arange(task_control.MAX_TRIALS):

    next_trial_state_machine = task_control.next_trial()

    bpod.send_state_machine(sma=next_trial_state_machine)

    if not bpod.run_state_machine(next_trial_state_machine):
        logging.debug(f"State machine did not return anything on trial {trial_index}")
        break

    task_data.append(trial_data=bpod.session.current_trial.export())

    # todo: update online plotting here

    # update task control on trial outcome
    task_control.update_task_progress()

task_data.save()
bpod.close()

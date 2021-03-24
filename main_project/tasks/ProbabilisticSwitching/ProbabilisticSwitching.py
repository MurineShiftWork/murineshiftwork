import logging

import numpy as np
import matplotlib.pyplot as plt
from pybpodapi.protocol import Bpod

from task_objects import TaskControl, TaskData, OnlinePlotting
from .tools import softcode_handler

bpod = Bpod(serial_port=None)
task_control = TaskControl(bpod=bpod)
task_data = TaskData(save_path="test")  # fixme: get savepath from session path
online_plotting = OnlinePlotting()


def bpod_loop_handler():
    f.canvas.flush_events()


bpod.loop_handler = bpod_loop_handler
bpod.softcode_handler_function = softcode_handler()

print('bpod session path:', bpod.session.path)

for trial_index in np.arange(task_control.MAX_TRIALS):

    next_trial_state_machine = task_control.next_trial()

    bpod.send_state_machine(sma=next_trial_state_machine)

    if not bpod.run_state_machine(next_trial_state_machine):
        logging.debug(f"State machine did not return anything on trial {trial_index}")
        break

    task_data.append(trial_data=bpod.session.current_trial.export())

    # todo: update online plotting here
    online_plotting.update(task_data=task_data)

    # update task control on trial outcome
    task_control.update_task_progress(task_data)

task_data.save()
bpod.close()

import logging

import numpy as np
import matplotlib.pyplot as plt
from pybpodapi.protocol import Bpod, StateMachine

from task_objects import TaskControl, TaskData, OnlinePlotting
from .tools import softcode_handler

bpod = Bpod(serial_port=None)
task_control = TaskControl(bpod=bpod)
task_data = TaskData(save_path="test")  # fixme: get savepath from session path
online_plotting = OnlinePlotting()


def bpod_loop_handler():
    f.canvas.flush_events()


bpod.loop_handler = bpod_loop_handler
# bpod.softcode_handler_function = softcode_handler()

logging.debug('bpod session path:', bpod.session.path)

for trial_index in np.arange(task_control.MAX_TRIALS):

    # next_trial_state_machine = task_control.next_trial()
    next_trial_state_machine = StateMachine(bpod=bpod)

    next_trial_state_machine.add_state(
        state_name='WaitForPort2Poke',
        state_timer=1,
        state_change_conditions={Bpod.Events.Port2In: 'FlashStimulus'},
        output_actions=[(Bpod.OutputChannels.PWM2, 255)])
    next_trial_state_machine.add_state(
        state_name='FlashStimulus',
        state_timer=0.1,
        state_change_conditions={Bpod.Events.Tup: 'WaitForResponse'},
        output_actions=[(Bpod.OutputChannels.PWM1, 255)])

    bpod.send_state_machine(sma=next_trial_state_machine)

    if not bpod.run_state_machine(next_trial_state_machine):
        logging.debug(f"State machine did not return anything on trial {trial_index}")
        break

    # task_data.append(trial_data=bpod.session.current_trial.export())

    online_plotting.update(task_data=task_data)

    # update task control on trial outcome
    # task_control.update_task_progress(task_data)

task_data.save()
bpod.close()

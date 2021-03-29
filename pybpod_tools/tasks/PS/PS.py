import logging
import random

import matplotlib.pyplot as plt
import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QFileDialog

from pybpod_tools.external.PulsePal3 import PulsePalObject
from pybpod_tools.misc import get_session_file_basename
from pybpod_tools.misc import softcode_handler
from pybpod_tools.tasks.PS.task_objects import OnlinePlotting
from pybpod_tools.tasks.PS.task_objects import TaskControl
from pybpod_tools.tasks.PS.task_objects import TaskData


# Bpod startup
def bpod_loop_handler():
    online_plotting.figure.canvas.flush_events()


bpod = Bpod()
bpod.loop_handler = bpod_loop_handler
bpod.softcode_handler_function = softcode_handler

# Task objects
save_path_basename = get_session_file_basename(bpod)
task_control = TaskControl(bpod=bpod)
task_data = TaskData(
    save_path=save_path_basename
)  # fixme: get savepath from session path
online_plotting = OnlinePlotting(save_path=save_path_basename)

# TODO: move task param to GUI to adjust them
trialTypes = [1, 2]  # 1 (rewarded left) or 2 (rewarded right)

# RUN trials

for trial_index in np.arange(task_control.MAX_TRIALS):  # Main loop
    print("Trial: ", trial_index + 1)

    # TODO: move SMA to task control object
    # TODO: need multiple SMA for simple training tasks and for TTL init (ephys), air puff, light, stop signal white noise
    thisTrialType = random.choice(trialTypes)  # Randomly choose trial type
    if thisTrialType == 1:
        stimulus = Bpod.OutputChannels.PWM1  # set stimulus channel for trial type 1
        leftAction = "Reward"
        rightAction = "Punish"
        rewardValve = 1
    elif thisTrialType == 2:
        stimulus = Bpod.OutputChannels.PWM3  # set stimulus channel for trial type 1
        leftAction = "Punish"
        rightAction = "Reward"
        rewardValve = 3

    sma = StateMachine(bpod)

    sma.add_state(
        state_name="WaitForPort2Poke",
        state_timer=1,
        state_change_conditions={Bpod.Events.Port2In: "FlashStimulus"},
        output_actions=[(Bpod.OutputChannels.PWM2, 255)],
    )
    sma.add_state(
        state_name="FlashStimulus",
        state_timer=0.1,
        state_change_conditions={Bpod.Events.Tup: "WaitForResponse"},
        output_actions=[(stimulus, 255)],
    )
    sma.add_state(
        state_name="WaitForResponse",
        state_timer=1,
        state_change_conditions={
            Bpod.Events.Port1In: leftAction,
            Bpod.Events.Port3In: rightAction,
        },
        output_actions=[],
    )
    sma.add_state(
        state_name="Reward",
        state_timer=0.1,
        state_change_conditions={Bpod.Events.Tup: "exit"},
        output_actions=[(Bpod.OutputChannels.Valve, rewardValve)],
    )  # Reward correct choice
    sma.add_state(
        state_name="Punish",
        state_timer=3,
        state_change_conditions={Bpod.Events.Tup: "exit"},
        output_actions=[
            (Bpod.OutputChannels.LED, 1),
            (Bpod.OutputChannels.LED, 2),
            (Bpod.OutputChannels.LED, 3),
        ],
    )  # Signal incorrect choice

    # EXECUTE trial
    bpod.send_state_machine(sma)  # Send state machine description to Bpod device

    print("Waiting for poke. Reward: ", "left" if thisTrialType == 1 else "right")

    if not bpod.run_state_machine(sma):
        logging.info(f"No data returned on trial #{trial_index}. Terminating protocol.")

    # TODO: update task data
    online_plotting.update(task_data=task_data)

    # TODO: control task: (a) next block?, (b) trial types?

    print("Current trial info: {0}".format(bpod.session.current_trial))

# TODO: save data/figure
bpod.close()  # Disconnect Bpod
